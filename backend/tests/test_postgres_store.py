"""The scaffolding every Postgres-backed store shares: the tables are created and the store set up the
first time it is used, and a database error comes out as the store's own unavailable error."""

import pytest
from database_urls import TEST_DATABASE_URL as DATABASE_URL
from database_urls import database_is_reachable, unused_database_url
from sqlmodel import create_engine

from devbingo_backend.history import GameHistoryRecord, HistoryUnavailable
from devbingo_backend.postgres_store import PostgresStore


@pytest.fixture
def engine():
    if not database_is_reachable(DATABASE_URL):
        pytest.skip("no Postgres database is available")
    engine = create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


def store_on(engine, setup=None) -> PostgresStore:
    return PostgresStore(engine, [GameHistoryRecord], HistoryUnavailable, setup=setup)


def test_a_database_that_is_down_is_reported_as_the_stores_unavailable_error():
    engine = create_engine(unused_database_url(), connect_args={"connect_timeout": 2})

    with pytest.raises(HistoryUnavailable):
        with store_on(engine).session():
            pass


def test_an_error_raised_by_the_work_passes_through_untranslated(engine):
    class Refused(Exception):
        pass

    with pytest.raises(Refused):
        with store_on(engine).session():
            raise Refused


def test_the_setup_runs_once_however_many_sessions_are_opened(engine):
    setups = []
    store = store_on(engine, setup=setups.append)

    with store.session():
        pass
    with store.session():
        pass

    assert len(setups) == 1


def test_a_failed_setup_is_tried_again_on_the_next_session(engine):
    attempts = []

    def setup(session):
        attempts.append(session)
        if len(attempts) == 1:
            raise RuntimeError("seeding failed")

    store = store_on(engine, setup=setup)
    with pytest.raises(RuntimeError):
        with store.session():
            pass
    with store.session():
        pass

    assert len(attempts) == 2
