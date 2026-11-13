from fastapi.testclient import TestClient

from devbingo_backend import game as game_module
from devbingo_backend.app import create_app
from devbingo_backend.errors import ErrorCode

UNUSED_DATABASE = "postgresql+psycopg://x@127.0.0.1:1/x"


def all_game_errors() -> list[type[game_module.GameError]]:
    found, queue = [], list(game_module.GameError.__subclasses__())
    while queue:
        error = queue.pop()
        found.append(error)
        queue.extend(error.__subclasses__())
    return found


def test_every_game_error_declares_its_own_wire_code():
    errors = all_game_errors()

    assert errors, "the engine has no errors to check"
    for error in errors:
        assert "code" in vars(error), f"{error.__name__} declares no code"
        assert isinstance(error.code, ErrorCode)


def test_no_two_game_errors_share_a_wire_code():
    codes = [error.code for error in all_game_errors()]

    assert len(codes) == len(set(codes))


def test_the_openapi_schema_describes_every_socket_message():
    with TestClient(create_app(UNUSED_DATABASE)) as client:
        schemas = client.get("/openapi.json").json()["components"]["schemas"]

    for name in (
        "ErrorCode",
        "Prize",
        "HostLink",
        "JoinPayload",
        "TickPayload",
        "ClaimPayload",
        "JoinAck",
        "WatchAck",
        "DrawAck",
        "Accepted",
        "Refusal",
        "LobbyUpdated",
        "PrizeAwarded",
        "PrizeBoardEntry",
        "DrawAnnouncement",
    ):
        assert name in schemas, f"{name} is missing from the OpenAPI schema"


def test_every_error_code_reaches_the_openapi_schema():
    with TestClient(create_app(UNUSED_DATABASE)) as client:
        schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert set(schemas["ErrorCode"]["enum"]) == {code.value for code in ErrorCode}


def test_a_refusal_always_carries_ok_false_and_an_error_code():
    with TestClient(create_app(UNUSED_DATABASE)) as client:
        refusal = client.get("/openapi.json").json()["components"]["schemas"]["Refusal"]

    assert set(refusal["required"]) == {"ok", "error"}


def test_creating_a_game_returns_the_host_link_model():
    with TestClient(create_app(UNUSED_DATABASE)) as client:
        spec = client.get("/openapi.json").json()

    created = spec["paths"]["/games"]["post"]["responses"]["201"]["content"][
        "application/json"
    ]
    assert created["schema"]["$ref"].endswith("/HostLink")
    assert "CreateGameResponse" not in spec["components"]["schemas"]
