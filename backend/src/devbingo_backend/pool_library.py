"""The Pool Library: where pools are kept, behind a port the app and the tests plug into."""

from typing import Any, Protocol

from sqlalchemy.exc import SQLAlchemyError

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool import Pool
from devbingo_backend.pool_store import ensure_default_pool, load_default_pool


class PoolLibraryUnavailable(Exception):
    """The library cannot be reached right now, so no pool can be loaded."""


class PoolLibrary(Protocol):
    """The one source of pools. Ticket 14 adds save, list and load by id."""

    def load_default(self) -> Pool:
        """The built-in default pool. Raises PoolLibraryUnavailable if the library can't be read."""
        ...


class InMemoryPoolLibrary:
    """A library that holds the default pool in memory, with no database. For tests."""

    def __init__(self, default: Pool = DEFAULT_POOL) -> None:
        self._default = default

    def load_default(self) -> Pool:
        return self._default


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
