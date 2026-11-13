import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from pydantic.json_schema import models_json_schema
from sqlmodel import create_engine, text

from devbingo_backend.game import DEFAULT_WINDOW_SECONDS, GameRegistry
from devbingo_backend.games_api import build_games_router
from devbingo_backend.history import (
    HistoryStore,
    HistoryUnavailable,
    PostgresHistoryStore,
)
from devbingo_backend.history_api import history_router
from devbingo_backend.http_errors import register_error_handlers
from devbingo_backend.pool_library import PoolLibrary, PostgresPoolLibrary
from devbingo_backend.pools_api import build_pools_router
from devbingo_backend.realtime import build_socket_server
from devbingo_backend.wire import SOCKET_MODELS, HealthResponse

DEFAULT_DATABASE_URL = "postgresql+psycopg://bingo:bingo@localhost:5432/devbingo"


def create_app(
    database_url: str | None = None,
    pool_library: PoolLibrary | None = None,
    settlement_window_seconds: float | None = None,
    history_store: HistoryStore | None = None,
) -> FastAPI:
    """`settlement_window_seconds` is how long a settlement window stays open. Without it the
    SETTLEMENT_WINDOW_SECONDS environment variable is used, then one second."""
    url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_engine(url, connect_args={"connect_timeout": 2})
    history = history_store or PostgresHistoryStore(engine)

    def code_has_history(code: str) -> bool:
        # If history can't be read the code is treated as free: `save` refuses to overwrite, so
        # a clash still costs nothing but the new game's record.
        try:
            return history.exists(code)
        except HistoryUnavailable:
            return False

    window_seconds = (
        settlement_window_seconds
        if settlement_window_seconds is not None
        else float(os.environ.get("SETTLEMENT_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS))
    )
    registry = GameRegistry(
        on_ended=history.save,
        code_taken=code_has_history,
        window_seconds=window_seconds,
    )
    library = pool_library or PostgresPoolLibrary(engine)

    def database_is_up() -> bool:
        # A health probe must never raise: any failure means the database
        # can't be used right now, whatever the driver reports.
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return False
        return True

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(title="DeveloperBingo API", lifespan=lifespan)

    register_error_handlers(app)
    app.include_router(history_router(history))
    app.state.registry = registry

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        up = database_is_up()
        return HealthResponse(
            status="ok" if up else "degraded",
            database="up" if up else "down",
        )

    app.include_router(build_games_router(registry, library))
    app.include_router(build_pools_router(library))

    rest_openapi = app.openapi

    def openapi_with_socket_messages() -> dict:
        """The REST schema plus the messages that only travel over the socket."""
        schema = rest_openapi()
        _, socket_schemas = models_json_schema(
            [(model, "serialization") for model in SOCKET_MODELS],
            ref_template="#/components/schemas/{model}",
        )
        schema["components"]["schemas"].update(socket_schemas["$defs"])
        return schema

    app.openapi = openapi_with_socket_messages  # type: ignore[method-assign]

    socket_server = build_socket_server(registry)
    app.mount("/socket.io", socketio.ASGIApp(socket_server))

    return app
