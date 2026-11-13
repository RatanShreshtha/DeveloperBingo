"""An ended game's history over HTTP, and the wiring that stores a game when it ends."""

import asyncio
import logging

import pytest
from fastapi.testclient import TestClient
from helpers import names_on, start_and_draw_everything

from devbingo_backend.app import create_app
from devbingo_backend.game import GameAlreadyEnded, GameSummary, HostLink, PlayerRef
from devbingo_backend.history import HistoryUnavailable, InMemoryHistoryStore
from devbingo_backend.pool_library import InMemoryPoolLibrary
from devbingo_backend.prizes import Prize


class UnavailableHistoryStore:
    def save(self, summary):
        raise HistoryUnavailable

    def load(self, code):
        raise HistoryUnavailable

    def exists(self, code):
        raise HistoryUnavailable


@pytest.fixture
def store():
    return InMemoryHistoryStore()


@pytest.fixture
def client(store):
    app = create_app(pool_library=InMemoryPoolLibrary(), history_store=store, settlement_window_seconds=0.0)
    with TestClient(app) as c:
        yield c


def registry_of(client):
    return client.app.state.registry


def test_a_game_ended_by_the_host_has_its_draws_viewable_by_its_code(client):
    registry = registry_of(client)
    game = registry.create_game(InMemoryPoolLibrary().load_default(), pool_name="Default")
    registry.start(game)
    drawn = registry.draw(game)
    registry.end(game)

    response = client.get(f"/games/{game.code}/history")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == game.code
    assert body["reason"] == "host"
    assert body["pool_name"] == "Default"
    assert body["draws"] == [
        {"position": 1, "name": drawn.topic.name, "explanation": drawn.topic.explanation}
    ]
    assert body["claims"] == []
    assert [w["awarded_to"] for w in body["winners"]] == [[] for _ in Prize]


def test_a_full_house_game_shows_claims_with_outcomes_and_winners(client):
    registry = registry_of(client)
    game = registry.create_game(InMemoryPoolLibrary().load_default())
    ada = PlayerRef(game.code, "Ada")
    ticket = registry.join(ada).snapshot.ticket
    start_and_draw_everything(registry, game)
    for topic in names_on(ticket):
        registry.tick(ada, topic)
    # The app's registry schedules its windows on the running event loop, so the claim needs one:
    # the window has no length, so it closes as soon as the loop gets to it.
    async def claim_full_house():
        registry.claim(ada, Prize.FULL_HOUSE)
        await asyncio.sleep(0.05)

    asyncio.run(claim_full_house())

    body = client.get(f"/games/{game.code}/history").json()

    assert body["reason"] == "full_house"
    assert body["pool_name"] is None
    assert len(body["draws"]) == 90
    assert body["claims"] == [
        {"player": "Ada", "prize": "full_house", "accepted": True, "error": None}
    ]
    assert {"prize": "full_house", "awarded_to": ["Ada"]} in body["winners"]


def test_a_game_that_is_still_running_has_no_history_yet(client):
    game = registry_of(client).create_game(InMemoryPoolLibrary().load_default())

    assert client.get(f"/games/{game.code}/history").status_code == 404


def test_an_unknown_game_has_no_history(client):
    assert client.get("/games/NOPE12/history").status_code == 404


def test_history_reports_service_unavailable_when_the_store_is_down():
    app = create_app(pool_library=InMemoryPoolLibrary(), history_store=UnavailableHistoryStore())
    with TestClient(app) as client:
        assert client.get("/games/ABCDEF/history").status_code == 503


def test_a_failing_store_does_not_stop_a_game_ending(caplog):
    app = create_app(pool_library=InMemoryPoolLibrary(), history_store=UnavailableHistoryStore())
    with TestClient(app) as client:
        registry = registry_of(client)
        game = registry.create_game(InMemoryPoolLibrary().load_default())
        with caplog.at_level(logging.ERROR):
            registry.end(game)

        with pytest.raises(GameAlreadyEnded):
            registry.start(game)
    assert any(r.exc_info for r in caplog.records)


def end_game(client, link):
    registry_of(client).end(HostLink(**link))


def test_a_game_created_from_a_saved_pool_records_that_pools_name_in_its_history(client):
    topics = [{"name": f"T{n:02}", "explanation": f"T{n:02} explained"} for n in range(90)]
    pool_id = client.post("/pools", json={"name": "Platform Team", "topics": topics}).json()["id"]
    link = client.post("/games", json={"pool_id": pool_id}).json()
    end_game(client, link)

    assert client.get(f"/games/{link['code']}/history").json()["pool_name"] == "Platform Team"


def test_a_game_created_without_a_pool_records_the_default_pool_name(client):
    link = client.post("/games").json()
    end_game(client, link)

    assert client.get(f"/games/{link['code']}/history").json()["pool_name"] == "Default"


def test_a_code_that_already_has_history_is_never_given_to_a_new_game(store, monkeypatch):
    taken = "TAKEN1"
    store.save(GameSummary(taken, "host", None, (), (), {prize: () for prize in Prize}))
    letters = iter(taken + taken + "FRESH1")
    monkeypatch.setattr("devbingo_backend.game.secrets.choice", lambda _alphabet: next(letters))
    app = create_app(pool_library=InMemoryPoolLibrary(), history_store=store)

    with TestClient(app) as c:
        code = c.post("/games").json()["code"]

    assert code == "FRESH1"
    assert store.load(taken).reason == "host"


def test_a_game_can_still_be_created_when_the_history_store_is_down():
    app = create_app(pool_library=InMemoryPoolLibrary(), history_store=UnavailableHistoryStore())
    with TestClient(app) as c:
        assert c.post("/games").status_code == 201
