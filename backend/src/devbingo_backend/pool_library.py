"""The Pool Library: where pools are kept, behind a port the app and the tests plug into.

The library also decides what may be saved. `admit` holds every pool rule a new pool must meet, and
each adapter calls it first, so a pool one adapter refuses the other refuses too.
"""

import threading
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Field, Session, SQLModel, select

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool import POOL_SIZE, Pool, PoolError, Topic, build_pool

DEFAULT_POOL_NAME = "Default"

MAX_POOL_NAME = 80
MAX_TOPIC_NAME = 80
MAX_EXPLANATION = 300
MAX_TOPICS = POOL_SIZE


class PoolLibraryUnavailable(Exception):
    """The library cannot be reached right now, so no pool can be loaded."""


class PoolNotFound(Exception):
    """No pool in the library has that id."""


class PoolRuleBroken(PoolError):
    """A new pool broke a rule on its name or the size of its parts. `rule` names which."""

    def __init__(self, rule: str, message: str) -> None:
        super().__init__(message)
        self.rule = rule


@dataclass(frozen=True)
class SavedPool:
    name: str
    pool: Pool


@dataclass(frozen=True)
class PoolSummary:
    id: int
    name: str
    is_default: bool


def admit(name: str, topics: Sequence[Topic]) -> tuple[str, Pool]:
    """The rules a new pool must meet to be saved. Returns the trimmed name and the pool built
    from the trimmed topics, or raises a PoolError naming the first rule broken. The topic count
    is checked first of all, so an oversized request is turned away before its topics are read."""
    if len(topics) > MAX_TOPICS:
        raise PoolRuleBroken(
            "too_many_topics", f"a pool has at most {MAX_TOPICS} topics"
        )
    name = name.strip()
    if not name:
        raise PoolRuleBroken("empty_name", "a pool needs a name")
    if len(name) > MAX_POOL_NAME:
        raise PoolRuleBroken(
            "name_too_long", f"a pool name has at most {MAX_POOL_NAME} characters"
        )
    if name.casefold() == DEFAULT_POOL_NAME.casefold():
        raise PoolRuleBroken(
            "reserved_name", f'"{DEFAULT_POOL_NAME}" is the built-in pool\'s name'
        )
    trimmed = [Topic(topic.name.strip(), topic.explanation.strip()) for topic in topics]
    for topic in trimmed:
        if len(topic.name) > MAX_TOPIC_NAME:
            raise PoolRuleBroken(
                "topic_name_too_long",
                f"a topic name has at most {MAX_TOPIC_NAME} characters",
            )
        if len(topic.explanation) > MAX_EXPLANATION:
            raise PoolRuleBroken(
                "explanation_too_long",
                f"an explanation has at most {MAX_EXPLANATION} characters",
            )
    return name, build_pool(trimmed)


class PoolLibrary(Protocol):
    """The one source of pools: the read-only default, and saved custom pools shared by all hosts."""

    def load_default(self) -> Pool:
        """The built-in default pool. Raises PoolLibraryUnavailable if the library can't be read."""
        ...

    def save(self, name: str, topics: Sequence[Topic]) -> PoolSummary:
        """Keep a new pool under a name. Both are trimmed, and a PoolError names the first pool
        rule they break, with nothing saved. Returns the saved pool's summary, name as kept."""
        ...

    def list_pools(self) -> list[PoolSummary]:
        """Every pool, the default included, in the order they were added."""
        ...

    def get(self, pool_id: int) -> SavedPool:
        """The pool with this id together with its name. Raises PoolNotFound for an unknown id."""
        ...


class InMemoryPoolLibrary:
    """A library that holds the default pool in memory, with no database. For tests."""

    def __init__(self, default: Pool = DEFAULT_POOL) -> None:
        self._default = default
        # Id 1 is the default; saved pools follow.
        self._pools: dict[int, tuple[str, Pool]] = {1: (DEFAULT_POOL_NAME, default)}

    def load_default(self) -> Pool:
        return self._default

    def save(self, name: str, topics: Sequence[Topic]) -> PoolSummary:
        name, pool = admit(name, topics)
        pool_id = max(self._pools) + 1
        self._pools[pool_id] = (name, pool)
        return PoolSummary(pool_id, name, is_default=False)

    def list_pools(self) -> list[PoolSummary]:
        return [
            PoolSummary(pool_id, name, pool_id == 1)
            for pool_id, (name, _) in self._pools.items()
        ]

    def get(self, pool_id: int) -> SavedPool:
        try:
            name, pool = self._pools[pool_id]
        except KeyError:
            raise PoolNotFound(pool_id) from None
        return SavedPool(name, pool)


class PoolRecord(SQLModel, table=True):
    __tablename__ = "pools"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    is_default: bool = False


class PoolTopicRecord(SQLModel, table=True):
    __tablename__ = "pool_topics"

    id: int | None = Field(default=None, primary_key=True)
    pool_id: int = Field(foreign_key="pools.id", index=True)
    position: int
    name: str
    explanation: str


# SQLModel classes expose __table__ at runtime; ty can't see it.
_TABLES = [PoolRecord.__table__, PoolTopicRecord.__table__]  # ty: ignore[missing-attribute]

# One process holds the app's state (ADR 0001), so a process-wide lock is enough to stop two
# first requests from seeding the default pool twice.
_seed_lock = threading.Lock()


class PostgresPoolLibrary:
    """The library the app uses: pools stored in Postgres. The tables are created and the default
    seeded on first use, once, so the app can start while the database is down."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine
        self._ready = False

    def _ensure_ready(self) -> None:
        """Create the pool tables if needed and seed the default pool. Done once: a failed attempt
        leaves the library not ready, so the next call tries again."""
        if self._ready:
            return
        with _seed_lock:
            if self._ready:
                return
            SQLModel.metadata.create_all(self._engine, tables=_TABLES)
            with Session(self._engine) as session:
                existing = session.exec(
                    select(PoolRecord).where(PoolRecord.is_default == True)  # noqa: E712
                ).first()
                if existing is None:
                    self._add(session, DEFAULT_POOL_NAME, DEFAULT_POOL, is_default=True)
                    session.commit()
            self._ready = True

    @staticmethod
    def _add(
        session: Session, name: str, pool: Pool, is_default: bool = False
    ) -> PoolRecord:
        record = PoolRecord(name=name, is_default=is_default)
        session.add(record)
        session.flush()
        for position, topic in enumerate(pool.topics):
            session.add(
                PoolTopicRecord(
                    pool_id=record.id,  # ty: ignore[invalid-argument-type]  # set by the flush in _add
                    position=position,
                    name=topic.name,
                    explanation=topic.explanation,
                )
            )
        return record

    @staticmethod
    def _read(session: Session, record: PoolRecord) -> SavedPool:
        rows = session.exec(
            select(PoolTopicRecord)
            .where(PoolTopicRecord.pool_id == record.id)
            .order_by(PoolTopicRecord.position)  # ty: ignore[invalid-argument-type]  # SQLModel column
        ).all()
        return SavedPool(
            record.name, build_pool([Topic(row.name, row.explanation) for row in rows])
        )

    def load_default(self) -> Pool:
        try:
            self._ensure_ready()
            with Session(self._engine) as session:
                record = session.exec(
                    select(PoolRecord).where(PoolRecord.is_default == True)  # noqa: E712
                ).one()
                return self._read(session, record).pool
        except SQLAlchemyError:
            # The database can't be reached or queried right now. Anything else is a bug and
            # is left to surface rather than be mistaken for an outage.
            raise PoolLibraryUnavailable from None

    def save(self, name: str, topics: Sequence[Topic]) -> PoolSummary:
        name, pool = admit(name, topics)
        try:
            self._ensure_ready()
            with Session(self._engine) as session:
                record = self._add(session, name, pool)
                session.commit()
                return PoolSummary(record.id, name, is_default=False)  # ty: ignore[invalid-argument-type]  # set by the flush in _add
        except SQLAlchemyError:
            raise PoolLibraryUnavailable from None

    def list_pools(self) -> list[PoolSummary]:
        try:
            self._ensure_ready()
            with Session(self._engine) as session:
                records = session.exec(select(PoolRecord).order_by(PoolRecord.id)).all()  # ty: ignore[invalid-argument-type]  # SQLModel column
                return [PoolSummary(r.id, r.name, r.is_default) for r in records]  # ty: ignore[invalid-argument-type]  # set by the flush in _add
        except SQLAlchemyError:
            raise PoolLibraryUnavailable from None

    def get(self, pool_id: int) -> SavedPool:
        try:
            self._ensure_ready()
            with Session(self._engine) as session:
                record = session.get(PoolRecord, pool_id)
                if record is None:
                    raise PoolNotFound(pool_id)
                return self._read(session, record)
        except SQLAlchemyError:
            raise PoolLibraryUnavailable from None
