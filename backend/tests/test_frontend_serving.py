import pytest
from database_urls import unused_database_url
from fastapi.testclient import TestClient

from devbingo_backend.app import create_app

HTML = {"accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
JSON = {"accept": "application/json"}


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>the app</html>")
    (tmp_path / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / "favicon.svg").write_text("<svg></svg>")
    return tmp_path


@pytest.fixture
def client(dist):
    with TestClient(create_app(unused_database_url(), frontend_dir=dist)) as client:
        yield client


def test_browser_page_gets_the_app(client):
    response = client.get("/rules", headers=HTML)

    assert response.status_code == 200
    assert "the app" in response.text


def test_root_gets_the_app_for_a_browser(client):
    response = client.get("/", headers=HTML)

    assert "the app" in response.text


def test_game_page_gets_the_app_not_the_api_json(client):
    response = client.get("/games/ABCD/history", headers=HTML)

    assert "the app" in response.text


def test_api_request_for_a_game_still_gets_json(client):
    response = client.get("/games/ABCD", headers=JSON)

    assert response.status_code == 404
    assert "the app" not in response.text


def test_health_is_not_replaced_by_the_app(client):
    response = client.get("/health", headers=HTML)

    assert response.json()["status"] in {"ok", "degraded"}


def test_built_assets_are_served(client):
    response = client.get("/assets/app.js")

    assert response.status_code == 200
    assert "console.log" in response.text


def test_favicon_is_served(client):
    response = client.get("/favicon.svg")

    assert response.status_code == 200
    assert "<svg>" in response.text


def test_app_is_not_served_without_a_frontend_dir():
    with TestClient(create_app(unused_database_url())) as client:
        response = client.get("/rules", headers=HTML)

    assert response.status_code == 404


def test_frontend_dir_comes_from_the_environment(dist, monkeypatch):
    monkeypatch.setenv("FRONTEND_DIR", str(dist))
    with TestClient(create_app(unused_database_url())) as client:
        response = client.get("/rules", headers=HTML)

    assert "the app" in response.text


def test_missing_build_fails_at_startup(tmp_path):
    with pytest.raises(RuntimeError, match="npm run build"):
        create_app(unused_database_url(), frontend_dir=tmp_path)
