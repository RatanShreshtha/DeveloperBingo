from collections.abc import Sequence
from dataclasses import dataclass

from devbingo_backend.names import name_key

COLUMN_SIZES: tuple[int, ...] = (9, 10, 10, 10, 10, 10, 10, 10, 11)
POOL_SIZE = sum(COLUMN_SIZES)


class PoolError(ValueError):
    """Base class for pools that break the pool rules. `rule` names the rule that was broken, as
    the HTTP routes report it."""

    rule: str = "invalid_pool"


class PoolSizeError(PoolError):
    rule = "pool_size"


class EmptyTopicError(PoolError):
    rule = "empty_topic"


class DuplicateTopicError(PoolError):
    rule = "duplicate_topic"


@dataclass(frozen=True)
class Topic:
    name: str
    explanation: str


@dataclass(frozen=True)
class Pool:
    """A validated, immutable pool of topics. Build one with build_pool."""

    topics: tuple[Topic, ...]

    def columns(self) -> tuple[tuple[Topic, ...], ...]:
        """Split the topics into the nine fixed columns, in list order."""
        columns: list[tuple[Topic, ...]] = []
        start = 0
        for size in COLUMN_SIZES:
            columns.append(self.topics[start : start + size])
            start += size
        return tuple(columns)


def build_pool(topics: Sequence[Topic]) -> Pool:
    if len(topics) != POOL_SIZE:
        raise PoolSizeError(f"a pool needs {POOL_SIZE} topics, got {len(topics)}")

    seen: set[str] = set()
    for topic in topics:
        if not topic.name.strip() or not topic.explanation.strip():
            raise EmptyTopicError(f"topic {topic.name!r} needs a name and an explanation")
        key = name_key(topic.name)
        if key in seen:
            raise DuplicateTopicError(f"topic {topic.name!r} appears more than once")
        seen.add(key)

    return Pool(tuple(topics))
