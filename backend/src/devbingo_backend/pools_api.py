"""REST routes for the Pool Library: list, read and save pools."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devbingo_backend.pool import (
    DuplicateTopicError,
    EmptyTopicError,
    PoolError,
    PoolSizeError,
    Topic,
    build_pool,
)
from devbingo_backend.pool_library import PoolLibrary, PoolNotFound
from devbingo_backend.pool_store import DEFAULT_POOL_NAME
from devbingo_backend.wire import PoolResponse, TopicResponse


class PoolSummaryResponse(BaseModel):
    id: int
    name: str
    is_default: bool


MAX_POOL_NAME = 80
MAX_TOPIC_NAME = 80
MAX_EXPLANATION = 300
MAX_TOPICS = 90


class NewPool(BaseModel):
    name: str
    topics: list[TopicResponse]

    def refusal(self) -> "HTTPException | None":
        """The first input limit this request breaks, or None. Checked before the pool rules, and
        the topic count first of all so an oversized body is turned away before it is read."""
        if len(self.topics) > MAX_TOPICS:
            return _refusal("too_many_topics", f"a pool has at most {MAX_TOPICS} topics")
        name = self.name.strip()
        if not name:
            return _refusal("empty_name", "a pool needs a name")
        if len(name) > MAX_POOL_NAME:
            return _refusal("name_too_long", f"a pool name has at most {MAX_POOL_NAME} characters")
        if name.casefold() == DEFAULT_POOL_NAME.casefold():
            return _refusal("reserved_name", f'"{DEFAULT_POOL_NAME}" is the built-in pool\'s name')
        for topic in self.topics:
            if len(topic.name.strip()) > MAX_TOPIC_NAME:
                return _refusal(
                    "topic_name_too_long", f"a topic name has at most {MAX_TOPIC_NAME} characters"
                )
            if len(topic.explanation.strip()) > MAX_EXPLANATION:
                return _refusal(
                    "explanation_too_long", f"an explanation has at most {MAX_EXPLANATION} characters"
                )
        return None


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


def _refusal(rule: str, message: str) -> HTTPException:
    return HTTPException(status_code=422, detail={"rule": rule, "message": message})


def build_pools_router(library: PoolLibrary) -> APIRouter:
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
            return PoolResponse.from_pool(library.load(pool_id))
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
        refusal = body.refusal()
        if refusal is not None:
            raise refusal
        name = body.name.strip()
        try:
            pool = build_pool(
                [Topic(topic.name.strip(), topic.explanation.strip()) for topic in body.topics]
            )
        except PoolError as error:
            raise _refusal(_RULES.get(type(error), "invalid_pool"), str(error)) from None
        pool_id = library.save(name, pool)
        return PoolSummaryResponse(id=pool_id, name=name, is_default=False)

    return router
