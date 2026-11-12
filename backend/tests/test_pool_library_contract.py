"""What every Pool Library adapter must do, run against each adapter in turn."""

import pytest
from database_urls import TEST_DATABASE_URL as DATABASE_URL
from database_urls import database_is_reachable
from sqlmodel import create_engine

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool_library import InMemoryPoolLibrary, PostgresPoolLibrary



@pytest.fixture(params=["memory", "postgres"])
def library(request):
    if request.param == "memory":
        yield InMemoryPoolLibrary()
        return
    if not database_is_reachable(DATABASE_URL):
        pytest.skip("no Postgres database is available")
    engine = create_engine(DATABASE_URL)
    yield PostgresPoolLibrary(engine)
    engine.dispose()


def test_the_default_pool_has_ninety_topics_in_nine_columns(library):
    pool = library.load_default()

    assert [len(column) for column in pool.columns()] == [9, 10, 10, 10, 10, 10, 10, 10, 11]
    assert len(pool.topics) == 90


def test_the_default_pool_is_the_built_in_one_in_list_order(library):
    assert library.load_default().topics == DEFAULT_POOL.topics


def test_loading_the_default_pool_twice_gives_the_same_pool(library):
    assert library.load_default().topics == library.load_default().topics
