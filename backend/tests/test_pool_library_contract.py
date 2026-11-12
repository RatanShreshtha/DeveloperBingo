"""What every Pool Library adapter must do, run against each adapter in turn."""

import pytest
from database_urls import TEST_DATABASE_URL as DATABASE_URL
from database_urls import database_is_reachable
from sqlmodel import create_engine

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool import Topic, build_pool
from devbingo_backend.pool_library import InMemoryPoolLibrary, PoolNotFound, PostgresPoolLibrary


def custom_pool(prefix: str = "Custom"):
    return build_pool([Topic(f"{prefix}{n:02}", f"{prefix}{n:02} explained") for n in range(90)])



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


def test_a_saved_pool_loads_back_by_id_in_list_order(library):
    pool = custom_pool()

    pool_id = library.save("My pool", pool)

    assert library.load(pool_id).topics == pool.topics


def test_saved_pools_are_listed_with_their_names_and_the_default_flagged(library):
    pool_id = library.save("Listed pool", custom_pool("Listed"))

    listed = {item.id: item for item in library.list_pools()}

    assert listed[pool_id].name == "Listed pool"
    assert listed[pool_id].is_default is False
    defaults = [item for item in listed.values() if item.is_default]
    assert len(defaults) == 1


def test_the_default_pool_loads_by_its_listed_id(library):
    default = next(item for item in library.list_pools() if item.is_default)

    assert library.load(default.id).topics == library.load_default().topics


def test_each_save_gets_its_own_id(library):
    first = library.save("One", custom_pool("One"))
    second = library.save("Two", custom_pool("Two"))

    assert first != second
    assert library.load(first).topics != library.load(second).topics


def test_loading_an_unknown_id_is_refused(library):
    with pytest.raises(PoolNotFound):
        library.load(10**9)
