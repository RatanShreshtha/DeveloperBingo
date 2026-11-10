import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import socketio
from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import create_engine, text

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameNotFound, GameRegistry, NotHost
from devbingo_backend.realtime import build_socket_server

DEFAULT_DATABASE_URL = "postgresql+psycopg://bingo:bingo@localhost:5432/devbingo"


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["up", "down"]


class CreateGameResponse(BaseModel):
    code: str
    host_token: str


class LobbyResponse(BaseModel):
    players: list[str]


class TopicResponse(BaseModel):
    name: str
    explanation: str


class PoolResponse(BaseModel):
    columns: list[list[TopicResponse]]


def create_app(database_url: str | None = None) -> FastAPI:
    url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    engine = create_engine(url, connect_args={"connect_timeout": 2})
    registry = GameRegistry()

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

    @app.post("/games", status_code=201, response_model=CreateGameResponse)
    def create_game() -> CreateGameResponse:
        created = registry.create_game()
        return CreateGameResponse(code=created.code, host_token=created.host_token)

    @app.get("/games/{code}/lobby", response_model=LobbyResponse)
    def read_lobby(
        code: str,
        x_host_token: Annotated[str, Header()] = "",
    ) -> LobbyResponse:
        try:
            players = registry.lobby(code, x_host_token)
        except GameNotFound:
            raise HTTPException(status_code=404, detail="game not found") from None
        except NotHost:
            raise HTTPException(status_code=403, detail="host token required") from None
        return LobbyResponse(players=players)

    @app.post("/games/{code}/start", status_code=204)
    def start_game(
        code: str,
        x_host_token: Annotated[str, Header()] = "",
    ) -> Response:
        try:
            registry.start(code, x_host_token)
        except GameNotFound:
            raise HTTPException(status_code=404, detail="game not found") from None
        except NotHost:
            raise HTTPException(status_code=403, detail="host token required") from None
        return Response(status_code=204)

    @app.get("/pools/default", response_model=PoolResponse)
    def read_default_pool() -> PoolResponse:
        return PoolResponse(
            columns=[
                [TopicResponse(name=topic.name, explanation=topic.explanation) for topic in column]
                for column in DEFAULT_POOL.columns()
            ]
        )

    socket_server = build_socket_server(registry)
    app.mount("/socket.io", socketio.ASGIApp(socket_server))

    return app
