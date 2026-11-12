import pytest
from fastapi.testclient import TestClient

from devbingo_backend.app import create_app
from devbingo_backend.pool_library import InMemoryPoolLibrary
from devbingo_backend.wire import HostLink, PoolResponse
from unavailable import UnavailablePoolLibrary


def topics(prefix="Mine", count=90):
    return [{"name": f"{prefix}{n:02}", "explanation": f"{prefix}{n:02} explained"} for n in range(count)]


def make_client(library=None):
    return TestClient(create_app(pool_library=library or InMemoryPoolLibrary()))


def hosts_snapshot(client, created):
    """What the host of a game just created through the API is shown when they watch it."""
    return client.app.state.registry.host_snapshot(HostLink(**created.json()))


def test_a_saved_pool_is_listed_and_read_back_in_nine_columns():
    with make_client() as client:
        saved = client.post("/pools", json={"name": "Mine", "topics": topics()})
        listed = client.get("/pools").json()
        read = client.get(f"/pools/{saved.json()['id']}")

    assert saved.status_code == 201
    assert {"id": saved.json()["id"], "name": "Mine", "is_default": False} in listed
    assert sum(1 for item in listed if item["is_default"]) == 1
    columns = read.json()["columns"]
    assert [len(c) for c in columns] == [9, 10, 10, 10, 10, 10, 10, 10, 11]
    assert columns[0][0] == {"name": "Mine00", "explanation": "Mine00 explained"}


def test_an_unknown_pool_is_not_found():
    with make_client() as client:
        assert client.get("/pools/999").status_code == 404


def test_a_pool_with_the_wrong_number_of_topics_is_refused_naming_the_rule():
    with make_client() as client:
        response = client.post("/pools", json={"name": "Short", "topics": topics(count=89)})

    assert response.status_code == 422
    assert response.json()["detail"]["rule"] == "pool_size"
    assert "90" in response.json()["detail"]["message"]


def test_duplicate_topics_are_refused_ignoring_case():
    body = topics()
    body[1]["name"] = body[0]["name"].upper()
    with make_client() as client:
        response = client.post("/pools", json={"name": "Dupes", "topics": body})

    assert response.status_code == 422
    assert response.json()["detail"]["rule"] == "duplicate_topic"


def test_a_topic_without_an_explanation_is_refused():
    body = topics()
    body[5]["explanation"] = "  "
    with make_client() as client:
        response = client.post("/pools", json={"name": "Blank", "topics": body})

    assert response.status_code == 422
    assert response.json()["detail"]["rule"] == "empty_topic"


def test_a_pool_without_a_name_is_refused_and_not_saved():
    with make_client() as client:
        response = client.post("/pools", json={"name": "  ", "topics": topics()})
        listed = client.get("/pools").json()

    assert response.status_code == 422
    assert response.json()["detail"]["rule"] == "empty_name"
    assert len(listed) == 1


def test_a_refused_pool_is_not_saved():
    with make_client() as client:
        client.post("/pools", json={"name": "Short", "topics": topics(count=3)})
        assert len(client.get("/pools").json()) == 1


def test_the_default_pool_stays_read_only():
    with make_client() as client:
        default_id = next(p["id"] for p in client.get("/pools").json() if p["is_default"])
        assert client.put(f"/pools/{default_id}", json={}).status_code == 405
        assert client.delete(f"/pools/{default_id}").status_code == 405


def test_pool_routes_report_service_unavailable_when_the_library_is_down():
    with make_client(UnavailablePoolLibrary()) as client:
        assert client.get("/pools").status_code == 503
        assert client.get("/pools/1").status_code == 503
        assert client.post("/pools", json={"name": "x", "topics": topics()}).status_code == 503


def test_a_game_created_with_a_saved_pool_deals_and_draws_from_it():
    with make_client() as client:
        pool_id = client.post("/pools", json={"name": "Mine", "topics": topics()}).json()["id"]
        game = client.post("/games", json={"pool_id": pool_id})
        assert game.status_code == 201
        shown = hosts_snapshot(client, game).pool.columns()

    assert shown[0][0].name == "Mine00"


def test_a_game_with_no_body_uses_the_default_pool():
    with make_client() as client:
        shown = hosts_snapshot(client, client.post("/games")).pool
        default = client.get("/pools/default").json()

    assert PoolResponse.from_pool(shown).model_dump() == default


def test_a_game_with_an_unknown_pool_id_is_not_found_and_creates_nothing():
    with make_client() as client:
        response = client.post("/games", json={"pool_id": 999})

    assert response.status_code == 404


def refusal_of(client, **overrides):
    body = {"name": "Limits", "topics": topics()}
    body.update(overrides)
    response = client.post("/pools", json=body)
    assert response.status_code == 422
    return response.json()["detail"]


def test_a_pool_name_over_eighty_characters_is_refused_naming_the_limit():
    with make_client() as client:
        detail = refusal_of(client, name="x" * 81)

    assert detail["rule"] == "name_too_long"
    assert "80" in detail["message"]


def test_a_pool_name_of_eighty_characters_after_trimming_is_kept_trimmed():
    with make_client() as client:
        saved = client.post("/pools", json={"name": "  " + "x" * 80 + "  ", "topics": topics()})

    assert saved.status_code == 201
    assert saved.json()["name"] == "x" * 80


def test_a_topic_name_over_eighty_characters_is_refused_naming_the_limit():
    body = topics()
    body[3]["name"] = "n" * 81
    with make_client() as client:
        detail = refusal_of(client, topics=body)

    assert detail["rule"] == "topic_name_too_long"
    assert "80" in detail["message"]


def test_an_explanation_over_three_hundred_characters_is_refused_naming_the_limit():
    body = topics()
    body[3]["explanation"] = "e" * 301
    with make_client() as client:
        detail = refusal_of(client, topics=body)

    assert detail["rule"] == "explanation_too_long"
    assert "300" in detail["message"]


def test_more_than_ninety_topics_are_refused_before_the_pool_rules_run():
    with make_client() as client:
        detail = refusal_of(client, topics=topics(count=91))

    assert detail["rule"] == "too_many_topics"
    assert "90" in detail["message"]


def test_topic_names_and_explanations_are_stored_trimmed():
    body = topics()
    body[0] = {"name": "  Padded  ", "explanation": "  spaced out  "}
    with make_client() as client:
        pool_id = client.post("/pools", json={"name": "Trim", "topics": body}).json()["id"]
        first = client.get(f"/pools/{pool_id}").json()["columns"][0][0]

    assert first == {"name": "Padded", "explanation": "spaced out"}


@pytest.mark.parametrize("name", ["Default", "default", "  DEFAULT "])
def test_a_pool_named_default_is_refused_so_the_picker_has_one_default(name):
    with make_client() as client:
        detail = refusal_of(client, name=name)
        listed = client.get("/pools").json()

    assert detail["rule"] == "reserved_name"
    assert len(listed) == 1


def test_a_game_created_from_a_saved_pool_tells_the_host_the_pools_name():
    with make_client() as client:
        pool_id = client.post("/pools", json={"name": "Mine", "topics": topics()}).json()["id"]
        shown = hosts_snapshot(client, client.post("/games", json={"pool_id": pool_id}))

    assert shown.pool_name == "Mine"


def test_a_game_on_the_default_pool_tells_the_host_it_is_the_default():
    with make_client() as client:
        assert hosts_snapshot(client, client.post("/games")).pool_name == "Default"
