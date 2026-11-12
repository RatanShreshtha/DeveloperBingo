"""REST routes for the Pool Library: list, read and save pools, and read a game's pool."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devbingo_backend.game import GameNotFound, GameRegistry
from devbingo_backend.pool import (
    DuplicateTopicError,
    EmptyTopicError,
    Pool,
    PoolError,
    PoolSizeError,
    Topic,
    build_pool,
)
from devbingo_backend.pool_library import PoolLibrary, PoolNotFound


class TopicResponse(BaseModel):
    name: str
    explanation: str


class PoolResponse(BaseModel):
    columns: list[list[TopicResponse]]


class PoolSummaryResponse(BaseModel):
    id: int
    name: str
    is_default: bool


class NewPool(BaseModel):
    name: str
    topics: list[TopicResponse]


class PoolRefusal(BaseModel):
    rule: str
    message: str


class PoolRefused(BaseModel):
    detail: PoolRefusal


_RULES: dict[type[PoolError], str] = {
    PoolSizeError: "pool_size",
    EmptyTopicError: "empty_topic",
    DuplicateTopicError: "duplicate_topic",
}


def pool_response(pool: Pool) -> PoolResponse:
    return PoolResponse(
        columns=[
            [TopicResponse(name=topic.name, explanation=topic.explanation) for topic in column]
            for column in pool.columns()
        ]
    )


def _refusal(rule: str, message: str) -> HTTPException:
    return HTTPException(status_code=422, detail={"rule": rule, "message": message})


def build_pools_router(library: PoolLibrary, registry: GameRegistry) -> APIRouter:
    router = APIRouter()

    @router.get("/pools", response_model=list[PoolSummaryResponse])
    def list_pools() -> list[PoolSummaryResponse]:
        return [
            PoolSummaryResponse(id=item.id, name=item.name, is_default=item.is_default)
            for item in library.list_pools()
        ]

    @router.get("/pools/{pool_id}", response_model=PoolResponse)
    def read_pool(pool_id: int) -> PoolResponse:
        try:
            return pool_response(library.load(pool_id))
        except PoolNotFound:
            raise HTTPException(status_code=404, detail="pool not found") from None

    @router.post(
        "/pools",
        status_code=201,
        response_model=PoolSummaryResponse,
        responses={422: {"model": PoolRefused}},
    )
    def save_pool(body: NewPool) -> PoolSummaryResponse:
        """Save a custom pool for every host to use, once it meets the pool rules."""
        name = body.name.strip()
        if not name:
            raise _refusal("empty_name", "a pool needs a name")
        try:
            pool = build_pool([Topic(topic.name, topic.explanation) for topic in body.topics])
        except PoolError as error:
            raise _refusal(_RULES.get(type(error), "invalid_pool"), str(error)) from None
        pool_id = library.save(name, pool)
        return PoolSummaryResponse(id=pool_id, name=name, is_default=False)

    @router.get("/games/{code}/pool", response_model=PoolResponse)
    def read_game_pool(code: str) -> PoolResponse:
        try:
            return pool_response(registry.pool_of(code))
        except GameNotFound:
            raise HTTPException(status_code=404, detail="game not found") from None

    return router
