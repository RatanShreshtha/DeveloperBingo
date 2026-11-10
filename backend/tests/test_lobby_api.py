from fastapi.testclient import TestClient

from devbingo_backend.app import create_app

HOST_HEADER = "X-Host-Token"


def create_game(client: TestClient) -> dict:
    response = client.post("/games")
    assert response.status_code == 201
    return response.json()


def test_creating_a_game_returns_a_code_and_a_host_token():
    with TestClient(create_app("postgresql+psycopg://x@127.0.0.1:1/x")) as client:
        game = create_game(client)

    assert game["code"]
    assert game["host_token"]


def test_the_host_token_reads_the_lobby():
    with TestClient(create_app("postgresql+psycopg://x@127.0.0.1:1/x")) as client:
        game = create_game(client)

        response = client.get(
            f"/games/{game['code']}/lobby",
            headers={HOST_HEADER: game["host_token"]},
        )

    assert response.status_code == 200
    assert response.json() == {"players": []}


def test_the_lobby_is_not_readable_without_the_host_token():
    with TestClient(create_app("postgresql+psycopg://x@127.0.0.1:1/x")) as client:
        game = create_game(client)

        missing = client.get(f"/games/{game['code']}/lobby")
        wrong = client.get(
            f"/games/{game['code']}/lobby",
            headers={HOST_HEADER: "not-the-host-token"},
        )

    assert missing.status_code == 403
    assert wrong.status_code == 403


def test_an_unknown_game_code_is_not_found():
    with TestClient(create_app("postgresql+psycopg://x@127.0.0.1:1/x")) as client:
        response = client.get(
            "/games/NOPE00/lobby", headers={HOST_HEADER: "anything"}
        )

    assert response.status_code == 404


