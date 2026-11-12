import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import socketio
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic.json_schema import models_json_schema
from sqlmodel import create_engine, text

from devbingo_backend.game import GameNotFound, GameRegistry, NotHost
from devbingo_backend.history import HistoryStore, HistoryUnavailable, PostgresHistoryStore
from devbingo_backend.history_api import history_router
from devbingo_backend.pool_library import (
    PoolLibrary,
    PoolLibraryUnavailable,
    PoolNotFound,
    PostgresPoolLibrary,
)
from devbingo_backend.pool_store import DEFAULT_POOL_NAME
from devbingo_backend.pools_api import PoolResponse, build_pools_router, pool_response
from devbingo_backend.realtime import DEFAULT_WINDOW_SECONDS, build_socket_server
from devbingo_backend.wire import SOCKET_MODELS, DrawAnnouncement, DrawHistoryResponse, HostLink

DEFAULT_DATABASE_URL = "postgresql+psycopg://bingo:bingo@localhost:5432/devbingo"


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["up", "down"]


class LobbyResponse(BaseModel):
    players: list[str]


class CreateGameRequest(BaseModel):
    pool_id: int | None = None


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

    registry = GameRegistry(on_ended=history.save, code_taken=code_has_history)
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

    @app.exception_handler(PoolLibraryUnavailable)
    def pool_library_unavailable(_request: Request, _error: PoolLibraryUnavailable) -> JSONResponse:
        """Whatever needed a pool gets a 503 when the library can't be read, with no fallback."""
        return JSONResponse(status_code=503, content={"detail": "pool library unavailable"})

    app.include_router(history_router(history))
    app.state.registry = registry

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        up = database_is_up()
        return HealthResponse(
            status="ok" if up else "degraded",
            database="up" if up else "down",
        )

    @app.post("/games", status_code=201, response_model=HostLink)
    def create_game(body: CreateGameRequest | None = None) -> HostLink:
        """Create a game on the default pool, or on the saved pool named by `pool_id`."""
        if body is None or body.pool_id is None:
            return registry.create_game(library.load_default(), pool_name=DEFAULT_POOL_NAME)
        try:
            saved = library.get(body.pool_id)
        except PoolNotFound:
            raise HTTPException(status_code=404, detail="pool not found") from None
        return registry.create_game(saved.pool, pool_name=saved.name)

    @app.get("/games/{code}/lobby", response_model=LobbyResponse)
    def read_lobby(
        code: str,
        x_host_token: Annotated[str, Header()] = "",
    ) -> LobbyResponse:
        try:
            players = registry.lobby(HostLink(code=code, host_token=x_host_token))
        except GameNotFound:
            raise HTTPException(status_code=404, detail="game not found") from None
        except NotHost:
            raise HTTPException(status_code=403, detail="host token required") from None
        return LobbyResponse(players=players)

    @app.get("/games/{code}/draws", response_model=DrawHistoryResponse)
    def read_draw_history(code: str) -> DrawHistoryResponse:
        """Every draw so far, in order. Public, so a player who arrives late can catch up."""
        try:
            draws = registry.draw_history(code)
        except GameNotFound:
            raise HTTPException(status_code=404, detail="game not found") from None
        return DrawHistoryResponse(
            draws=[DrawAnnouncement.from_draw(draw) for draw in draws],
        )

    @app.get("/pools/default", response_model=PoolResponse)
    def read_default_pool() -> PoolResponse:
        return pool_response(library.load_default())

    app.include_router(build_pools_router(library, registry))

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

    window_seconds = (
        settlement_window_seconds
        if settlement_window_seconds is not None
        else float(os.environ.get("SETTLEMENT_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS))
    )
    socket_server = build_socket_server(registry, window_seconds)
    app.mount("/socket.io", socketio.ASGIApp(socket_server))

    return app
