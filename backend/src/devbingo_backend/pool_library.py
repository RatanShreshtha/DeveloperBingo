"""The Pool Library: where pools are kept, behind a port the app and the tests plug into."""

from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool import Pool, Topic, build_pool
from devbingo_backend.pool_store import (
    PoolRecord,
    PoolTopicRecord,
    ensure_default_pool,
    load_default_pool,
)


class PoolLibraryUnavailable(Exception):
    """The library cannot be reached right now, so no pool can be loaded."""


class PoolNotFound(Exception):
    """No pool in the library has that id."""


@dataclass(frozen=True)
class PoolSummary:
    id: int
    name: str
    is_default: bool


class PoolLibrary(Protocol):
    """The one source of pools: the read-only default, and saved custom pools shared by all hosts."""

    def load_default(self) -> Pool:
        """The built-in default pool. Raises PoolLibraryUnavailable if the library can't be read."""
        ...

    def save(self, name: str, pool: Pool) -> int:
        """Keep a validated pool under a name and return its new id."""
        ...

    def list_pools(self) -> list[PoolSummary]:
        """Every pool, the default included, in the order they were added."""
        ...

    def load(self, pool_id: int) -> Pool:
        """The pool with this id. Raises PoolNotFound for an unknown id."""
        ...


class InMemoryPoolLibrary:
    """A library that holds the default pool in memory, with no database. For tests."""

    def __init__(self, default: Pool = DEFAULT_POOL) -> None:
        self._default = default
        # Id 1 is the default; saved pools follow.
        self._pools: dict[int, tuple[str, Pool]] = {1: ("Default", default)}

    def load_default(self) -> Pool:
        return self._default

    def save(self, name: str, pool: Pool) -> int:
        pool_id = max(self._pools) + 1
        self._pools[pool_id] = (name, pool)
        return pool_id

    def list_pools(self) -> list[PoolSummary]:
        return [PoolSummary(pool_id, name, pool_id == 1) for pool_id, (name, _) in self._pools.items()]

    def load(self, pool_id: int) -> Pool:
        try:
            return self._pools[pool_id][1]
        except KeyError:
            raise PoolNotFound(pool_id) from None


class PostgresPoolLibrary:
    """The library the app uses: pools stored in Postgres, with the default seeded on first use."""

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    def load_default(self) -> Pool:
        try:
            ensure_default_pool(self._engine)
            return load_default_pool(self._engine)
        except SQLAlchemyError:
            # The database can't be reached or queried right now. Anything else is a bug and
            # is left to surface rather than be mistaken for an outage.
            raise PoolLibraryUnavailable from None

    def save(self, name: str, pool: Pool) -> int:
        try:
            ensure_default_pool(self._engine)
            with Session(self._engine) as session:
                record = PoolRecord(name=name, is_default=False)
                session.add(record)
                session.flush()
                for position, topic in enumerate(pool.topics):
                    session.add(
                        PoolTopicRecord(
                            pool_id=record.id,
                            position=position,
                            name=topic.name,
                            explanation=topic.explanation,
                        )
                    )
                session.commit()
                return record.id
        except SQLAlchemyError:
            raise PoolLibraryUnavailable from None

    def list_pools(self) -> list[PoolSummary]:
        try:
            ensure_default_pool(self._engine)
            with Session(self._engine) as session:
                records = session.exec(select(PoolRecord).order_by(PoolRecord.id)).all()
                return [PoolSummary(r.id, r.name, r.is_default) for r in records]
        except SQLAlchemyError:
            raise PoolLibraryUnavailable from None

    def load(self, pool_id: int) -> Pool:
        try:
            ensure_default_pool(self._engine)
            with Session(self._engine) as session:
                if session.get(PoolRecord, pool_id) is None:
                    raise PoolNotFound(pool_id)
                rows = session.exec(
                    select(PoolTopicRecord)
                    .where(PoolTopicRecord.pool_id == pool_id)
                    .order_by(PoolTopicRecord.position)
                ).all()
            return build_pool([Topic(row.name, row.explanation) for row in rows])
        except SQLAlchemyError:
            raise PoolLibraryUnavailable from None
