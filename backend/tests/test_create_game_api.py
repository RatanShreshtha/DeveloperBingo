from fastapi.testclient import TestClient

from devbingo_backend.app import create_app
from devbingo_backend.pool_library import InMemoryPoolLibrary
from unavailable import UnavailablePoolLibrary

def create_game(client: TestClient) -> dict:
    response = client.post("/games")
    assert response.status_code == 201
    return response.json()


def test_creating_a_game_returns_a_code_and_a_host_token():
    with TestClient(create_app(pool_library=InMemoryPoolLibrary())) as client:
        game = create_game(client)

    assert game["code"]
    assert game["host_token"]


def test_creating_a_game_reports_service_unavailable_when_the_pool_library_is_down():
    with TestClient(create_app(pool_library=UnavailablePoolLibrary())) as client:
        response = client.post("/games")

    assert response.status_code == 503
