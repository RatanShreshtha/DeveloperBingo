
import pytest
from database_urls import TEST_DATABASE_URL as DATABASE_URL
from database_urls import database_is_reachable
from sqlmodel import Session, create_engine, select

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool_store import (
    PoolRecord,
    PoolTopicRecord,
    ensure_default_pool,
    load_default_pool,
)



@pytest.fixture
def engine():
    if not database_is_reachable(DATABASE_URL):
        pytest.skip("no Postgres database is available")
    engine = create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


def default_pool_rows(engine):
    with Session(engine) as session:
        return session.exec(
            select(PoolRecord).where(PoolRecord.is_default == True)  # noqa: E712
        ).all()


def test_the_default_pool_is_seeded_as_one_row_with_ninety_topics(engine):
    ensure_default_pool(engine)

    pools = default_pool_rows(engine)
    assert len(pools) == 1
    with Session(engine) as session:
        topics = session.exec(
            select(PoolTopicRecord).where(PoolTopicRecord.pool_id == pools[0].id)
        ).all()
    assert len(topics) == 90


def test_seeding_twice_does_not_duplicate_the_default_pool(engine):
    ensure_default_pool(engine)
    ensure_default_pool(engine)

    assert len(default_pool_rows(engine)) == 1


def test_loading_the_default_pool_returns_its_topics_in_seeded_order(engine):
    ensure_default_pool(engine)

    loaded = load_default_pool(engine)

    assert loaded.topics == DEFAULT_POOL.topics


def test_the_postgres_library_reports_unavailable_when_the_database_is_down():
    from database_urls import unused_database_url
    from devbingo_backend.pool_library import PoolLibraryUnavailable, PostgresPoolLibrary

    library = PostgresPoolLibrary(create_engine(unused_database_url(), connect_args={"connect_timeout": 2}))

    with pytest.raises(PoolLibraryUnavailable):
        library.load_default()
