"""What every History Store adapter must do, run against each adapter in turn."""

import uuid

import pytest
from database_urls import TEST_DATABASE_URL as DATABASE_URL
from database_urls import database_is_reachable
from sqlmodel import create_engine

from devbingo_backend.game import Draw, GameSummary
from devbingo_backend.history import AlreadyStored, InMemoryHistoryStore, PostgresHistoryStore
from devbingo_backend.pool import Topic
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord
from devbingo_backend.errors import ErrorCode


@pytest.fixture(params=["memory", "postgres"])
def store(request):
    if request.param == "memory":
        yield InMemoryHistoryStore()
        return
    if not database_is_reachable(DATABASE_URL):
        pytest.skip("no Postgres database is available")
    engine = create_engine(DATABASE_URL)
    yield PostgresHistoryStore(engine)
    engine.dispose()


def summary(code: str = "CONTRACT1", reason="full_house", pool_name="Backend basics") -> GameSummary:
    awarded = {Prize.EARLY_FIVE: ("Ada",), Prize.FULL_HOUSE: ("Ada", "Linus")}
    return GameSummary(
        code=code,
        end_reason=reason,
        pool_name=pool_name,
        draws=(Draw(1, Topic("Cache", "Keeps results close")), Draw(2, Topic("Index", "Speeds lookups"))),
        claims=(
            ClaimRecord("Grace", Prize.EARLY_FIVE, accepted=False, error=ErrorCode.CLAIM_NOT_VALID),
            ClaimRecord("Ada", Prize.EARLY_FIVE, accepted=True),
            ClaimRecord("Ada", Prize.FULL_HOUSE, accepted=True),
            ClaimRecord("Linus", Prize.FULL_HOUSE, accepted=True),
        ),
        prizes={prize: awarded.get(prize, ()) for prize in Prize},
    )


@pytest.fixture
def code():
    """A code no earlier run left in a persistent database."""
    return uuid.uuid4().hex[:12].upper()


def test_a_stored_game_comes_back_exactly_as_saved(store, code):
    saved = summary(code)
    store.save(saved)

    assert store.load(code) == saved


def test_a_game_with_no_pool_name_and_nothing_else_round_trips(store, code):
    bare = GameSummary(code, "host", None, (), (), {prize: () for prize in Prize})
    store.save(bare)

    assert store.load(code) == bare


def test_an_unknown_game_has_no_history(store):
    assert store.load("NOSUCHGAME") is None


def test_saving_a_game_again_is_refused_and_keeps_the_first_history(store, code):
    store.save(summary(code, reason="host"))

    with pytest.raises(AlreadyStored):
        store.save(summary(code, reason="full_house"))

    assert store.load(code) == summary(code, reason="host")


def test_a_stored_game_exists_and_an_unknown_one_does_not(store, code):
    store.save(summary(code))

    assert store.exists(code) is True
    assert store.exists("NOSUCHGAME") is False
