"""What every Pool Library adapter must do, run against each adapter in turn."""

import pytest
from database_urls import TEST_DATABASE_URL as DATABASE_URL
from database_urls import database_is_reachable, unused_database_url
from sqlmodel import create_engine

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool import PoolError, Topic
from devbingo_backend.pool_library import (
    DEFAULT_POOL_NAME,
    InMemoryPoolLibrary,
    PoolLibraryUnavailable,
    PoolNotFound,
    PostgresPoolLibrary,
)


def custom_topics(prefix: str = "Custom", count: int = 90) -> list[Topic]:
    return [Topic(f"{prefix}{n:02}", f"{prefix}{n:02} explained") for n in range(count)]


@pytest.fixture
def postgres_engine():
    if not database_is_reachable(DATABASE_URL):
        pytest.skip("no Postgres database is available")
    engine = create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


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

    assert [len(column) for column in pool.columns()] == [
        9,
        10,
        10,
        10,
        10,
        10,
        10,
        10,
        11,
    ]
    assert len(pool.topics) == 90


def test_the_default_pool_is_the_built_in_one_in_list_order(library):
    assert library.load_default().topics == DEFAULT_POOL.topics


def test_loading_the_default_pool_twice_gives_the_same_pool(library):
    assert library.load_default().topics == library.load_default().topics


def test_a_saved_pool_loads_back_by_id_in_list_order(library):
    topics = custom_topics()

    saved = library.save("My pool", topics)

    assert library.get(saved.id).pool.topics == tuple(topics)


def test_saving_returns_the_pool_as_listed(library):
    saved = library.save("Listed pool", custom_topics("Listed"))

    assert (saved.name, saved.is_default) == ("Listed pool", False)
    assert saved in library.list_pools()


def test_saved_pools_are_listed_with_their_names_and_the_default_flagged(library):
    saved = library.save("Listed pool", custom_topics("Listed"))

    listed = {item.id: item for item in library.list_pools()}

    assert listed[saved.id].name == "Listed pool"
    assert listed[saved.id].is_default is False
    defaults = [item for item in listed.values() if item.is_default]
    assert len(defaults) == 1


def test_the_default_pool_loads_by_its_listed_id(library):
    default = next(item for item in library.list_pools() if item.is_default)

    assert library.get(default.id).pool.topics == library.load_default().topics


def test_each_save_gets_its_own_id(library):
    first = library.save("One", custom_topics("One"))
    second = library.save("Two", custom_topics("Two"))

    assert first.id != second.id
    assert library.get(first.id).pool.topics != library.get(second.id).pool.topics


def test_a_pool_comes_back_by_id_with_its_name(library):
    topics = custom_topics("Named")
    saved = library.save("Named pool", topics)

    got = library.get(saved.id)

    assert got.name == "Named pool"
    assert got.pool.topics == tuple(topics)


def test_the_default_pool_is_got_under_the_one_default_name(library):
    default = next(item for item in library.list_pools() if item.is_default)

    assert default.name == DEFAULT_POOL_NAME
    assert library.get(default.id).name == DEFAULT_POOL_NAME


def test_getting_an_unknown_id_is_refused(library):
    with pytest.raises(PoolNotFound):
        library.get(10**9)


# The pool rules. Each case breaks exactly one, except where it says otherwise.


def duplicated() -> list[Topic]:
    topics = custom_topics()
    topics[1] = Topic(topics[0].name.upper(), "another explanation")
    return topics


def blank_explanation() -> list[Topic]:
    topics = custom_topics()
    topics[5] = Topic(topics[5].name, "  ")
    return topics


def long_topic_name() -> list[Topic]:
    topics = custom_topics()
    topics[3] = Topic("n" * 81, "explained")
    return topics


def long_explanation() -> list[Topic]:
    topics = custom_topics()
    topics[3] = Topic(topics[3].name, "e" * 301)
    return topics


RULE_CASES = [
    ("Mine", custom_topics(count=89), "pool_size", "90"),
    ("Mine", duplicated(), "duplicate_topic", None),
    ("Mine", blank_explanation(), "empty_topic", None),
    ("  ", custom_topics(), "empty_name", None),
    ("x" * 81, custom_topics(), "name_too_long", "80"),
    ("Default", custom_topics(), "reserved_name", None),
    ("default", custom_topics(), "reserved_name", None),
    ("  DEFAULT ", custom_topics(), "reserved_name", None),
    ("Mine", long_topic_name(), "topic_name_too_long", "80"),
    ("Mine", long_explanation(), "explanation_too_long", "300"),
    ("Mine", custom_topics(count=91), "too_many_topics", "90"),
    # Limits are checked before the pool rules: a long name wins over a short topic list.
    ("x" * 81, custom_topics(count=3), "name_too_long", "80"),
    # The topic count is checked first of all.
    ("  ", custom_topics(count=91), "too_many_topics", "90"),
]


@pytest.mark.parametrize(("name", "topics", "rule", "limit"), RULE_CASES)
def test_a_pool_that_breaks_a_rule_is_refused_naming_it_and_is_not_saved(
    library, name, topics, rule, limit
):
    before = library.list_pools()

    with pytest.raises(PoolError) as refused:
        library.save(name, topics)

    assert refused.value.rule == rule
    if limit is not None:
        assert limit in str(refused.value)
    assert library.list_pools() == before


def test_a_name_of_eighty_characters_after_trimming_is_kept_trimmed(library):
    saved = library.save("  " + "x" * 80 + "  ", custom_topics())

    assert saved.name == "x" * 80
    assert library.get(saved.id).name == "x" * 80


def test_topic_names_and_explanations_are_kept_trimmed(library):
    topics = custom_topics()
    topics[0] = Topic("  Padded  ", "  spaced out  ")

    saved = library.save("Trim", topics)

    assert library.get(saved.id).pool.topics[0] == Topic("Padded", "spaced out")


# Seeding the default pool in Postgres.


def test_two_libraries_on_one_database_keep_a_single_default_pool(postgres_engine):
    first = PostgresPoolLibrary(postgres_engine)
    second = PostgresPoolLibrary(postgres_engine)

    first.load_default()
    second.load_default()

    assert sum(1 for item in first.list_pools() if item.is_default) == 1


def test_the_postgres_library_reports_unavailable_when_the_database_is_down():
    library = PostgresPoolLibrary(
        create_engine(unused_database_url(), connect_args={"connect_timeout": 2})
    )

    with pytest.raises(PoolLibraryUnavailable):
        library.load_default()
    with pytest.raises(PoolLibraryUnavailable):
        library.save("Mine", custom_topics())
