import dataclasses

import pytest

from devbingo_backend.pool import (
    COLUMN_SIZES,
    POOL_SIZE,
    DuplicateTopicError,
    EmptyTopicError,
    PoolSizeError,
    Topic,
    build_pool,
)


def make_topics(count: int) -> list[Topic]:
    return [Topic(f"Topic {i}", f"Explanation {i}") for i in range(count)]


def test_a_pool_has_exactly_ninety_topics():
    assert POOL_SIZE == 90


def test_a_pool_with_89_topics_is_rejected():
    with pytest.raises(PoolSizeError):
        build_pool(make_topics(89))


def test_a_pool_with_91_topics_is_rejected():
    with pytest.raises(PoolSizeError):
        build_pool(make_topics(91))


def test_duplicate_topic_names_are_rejected_ignoring_case():
    topics = make_topics(89)
    topics.append(Topic("topic 0", "A second explanation"))

    with pytest.raises(DuplicateTopicError):
        build_pool(topics)


def test_a_topic_without_an_explanation_is_rejected():
    topics = make_topics(89)
    topics.append(Topic("Lonely topic", "   "))

    with pytest.raises(EmptyTopicError):
        build_pool(topics)


def test_a_topic_without_a_name_is_rejected():
    topics = make_topics(89)
    topics.append(Topic("", "Has an explanation"))

    with pytest.raises(EmptyTopicError):
        build_pool(topics)


def test_the_nine_columns_have_the_expected_sizes():
    assert COLUMN_SIZES == (9, 10, 10, 10, 10, 10, 10, 10, 11)
    assert sum(COLUMN_SIZES) == POOL_SIZE


def test_topics_fill_the_columns_in_list_order():
    pool = build_pool(make_topics(POOL_SIZE))

    columns = pool.columns()

    assert [len(column) for column in columns] == list(COLUMN_SIZES)
    flattened = [topic for column in columns for topic in column]
    assert flattened == list(pool.topics)
    assert columns[0][0].name == "Topic 0"
    assert columns[1][0].name == "Topic 9"
    assert columns[8][-1].name == "Topic 89"


def test_a_pool_cannot_be_edited_after_it_is_built():
    pool = build_pool(make_topics(POOL_SIZE))

    with pytest.raises(dataclasses.FrozenInstanceError):
        pool.topics = ()  # ty: ignore[invalid-assignment]  # frozen: the write must fail
    with pytest.raises(dataclasses.FrozenInstanceError):
        pool.topics[0].name = "Renamed"  # ty: ignore[invalid-assignment]  # frozen: the write must fail
