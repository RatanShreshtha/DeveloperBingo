import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import socketio
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from pydantic.json_schema import models_json_schema
from sqlmodel import create_engine, text

from devbingo_backend.game import GameNotFound, GameRegistry, NotHost
from devbingo_backend.pool_library import PoolLibrary, PoolLibraryUnavailable, PostgresPoolLibrary
from devbingo_backend.realtime import build_socket_server
from devbingo_backend.wire import SOCKET_MODELS, DrawAnnouncement, DrawHistoryResponse, HostLink

DEFAULT_DATABASE_URL = "postgresql+psycopg://bingo:bingo@localhost:5432/devbingo"


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["up", "down"]


class LobbyResponse(BaseModel):
    players: list[str]


class TopicResponse(BaseModel):
    name: str
    explanation: str


class PoolResponse(BaseModel):
    columns: list[list[TopicResponse]]


def create_app(database_url: str | None = None, pool_library: PoolLibrary | None = None) -> FastAPI:
    url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_engine(url, connect_args={"connect_timeout": 2})
    registry = GameRegistry()
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

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        up = database_is_up()
        return HealthResponse(
            status="ok" if up else "degraded",
            database="up" if up else "down",
        )

    @app.post("/games", status_code=201, response_model=HostLink)
    def create_game() -> HostLink:
        try:
            pool = library.load_default()
        except PoolLibraryUnavailable:
            raise HTTPException(status_code=503, detail="pool library unavailable") from None
        return registry.create_game(pool)

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
        try:
            pool = library.load_default()
        except PoolLibraryUnavailable:
            raise HTTPException(status_code=503, detail="pool library unavailable") from None
        return PoolResponse(
            columns=[
                [TopicResponse(name=topic.name, explanation=topic.explanation) for topic in column]
                for column in pool.columns()
            ]
        )

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
