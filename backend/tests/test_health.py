import os
import socket

from fastapi.testclient import TestClient

from devbingo_backend import app as app_module
from devbingo_backend.app import DEFAULT_DATABASE_URL, create_app

DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_DATABASE_URL)


class BrokenEngine:
    """A database engine whose driver fails on every connection attempt."""

    def connect(self):
        raise RuntimeError("driver failure")

    def dispose(self):
        pass


def unused_database_url() -> str:
    """A database URL pointing at a port nothing is listening on."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"postgresql+psycopg://bingo:bingo@127.0.0.1:{port}/devbingo"


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
