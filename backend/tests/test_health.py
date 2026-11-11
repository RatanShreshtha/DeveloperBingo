import os

from fastapi.testclient import TestClient

from devbingo_backend import app as app_module
from devbingo_backend.app import DEFAULT_DATABASE_URL, create_app
from database_urls import unused_database_url

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_DATABASE_URL)


class BrokenEngine:
    """A database engine whose driver fails on every connection attempt."""

    def connect(self):
        raise RuntimeError("driver failure")

    def dispose(self):
        pass


def test_health_reports_database_up():
    with TestClient(create_app(DATABASE_URL)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_health_reports_database_down_without_failing():
    with TestClient(create_app(unused_database_url())) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "database": "down"}


def test_health_reports_database_down_for_any_driver_error(monkeypatch):
    monkeypatch.setattr(
        app_module, "create_engine", lambda *args, **kwargs: BrokenEngine()
    )

    with TestClient(create_app(DATABASE_URL)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "database": "down"}


def test_openapi_describes_the_health_response():
    with TestClient(create_app(DATABASE_URL)) as client:
        schema = client.get("/openapi.json").json()

    health_schema = schema["components"]["schemas"]["HealthResponse"]
    assert set(health_schema["properties"]) == {"status", "database"}
