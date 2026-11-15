"""The scaffolding the Postgres-backed stores share. Each store keeps its own queries. This module
creates the store's tables and runs its setup the first time it is used, and turns a database error
into the store's own unavailable error."""

import threading
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, SQLModel

# One process holds the app's state (ADR 0001), so one lock stops two first uses from creating the
# tables twice.
_setup_lock = threading.Lock()


class PostgresStore:
    """The database a store works in. Its tables are created, and its setup run, once, the first time
    a session is opened, so the app can start while the database is down. A setup that fails leaves
    the store not ready, so the next session tries it again."""

    def __init__(
        self,
        engine: Any,
        models: Sequence[type[SQLModel]],
        unavailable: type[Exception],
        setup: Callable[[Session], None] | None = None,
    ) -> None:
        self._engine = engine
        # SQLModel classes expose __table__ at runtime; ty can't see it.
        self._tables = [model.__table__ for model in models]  # ty: ignore[missing-attribute]
        self._unavailable = unavailable
        self._setup = setup
        self._ready = False

    @contextmanager
    def session(self) -> Generator[Session]:
        """A session on the database. A database error, raised while opening it or by the work done
        in it, comes out as the store's unavailable error. Any other error passes through as it is."""
        try:
            self._ensure_ready()
            with Session(self._engine) as session:
                yield session
        except SQLAlchemyError:
            raise self._unavailable from None

    def _ensure_ready(self) -> None:
        if self._ready:
            return
        with _setup_lock:
            if self._ready:
                return
            SQLModel.metadata.create_all(self._engine, tables=self._tables)
            if self._setup is not None:
                with Session(self._engine) as session:
                    self._setup(session)
                    session.commit()
            self._ready = True
