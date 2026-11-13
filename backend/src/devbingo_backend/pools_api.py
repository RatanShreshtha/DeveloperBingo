"""REST routes for the Pool Library: list, read and save pools."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devbingo_backend.pool import PoolError, Topic
from devbingo_backend.pool_library import PoolLibrary, PoolNotFound
from devbingo_backend.wire import PoolRefused, PoolResponse, PoolSummaryResponse, TopicResponse


class NewPool(BaseModel):
    name: str
    topics: list[TopicResponse]


def _refusal(error: PoolError) -> HTTPException:
    return HTTPException(status_code=422, detail={"rule": error.rule, "message": str(error)})


def build_pools_router(library: PoolLibrary) -> APIRouter:
    router = APIRouter()

    # Declared before `/pools/{pool_id}`, so "default" is not read as an id.
    @router.get("/pools/default", response_model=PoolResponse)
    def read_default_pool() -> PoolResponse:
        return PoolResponse.from_pool(library.load_default())

    @router.get("/pools", response_model=list[PoolSummaryResponse])
    def list_pools() -> list[PoolSummaryResponse]:
        return [
            PoolSummaryResponse(id=item.id, name=item.name, is_default=item.is_default)
            for item in library.list_pools()
        ]

    @router.get("/pools/{pool_id}", response_model=PoolResponse)
    def read_pool(pool_id: int) -> PoolResponse:
        try:
            return PoolResponse.from_pool(library.get(pool_id).pool)
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
        try:
            saved = library.save(body.name, [Topic(topic.name, topic.explanation) for topic in body.topics])
        except PoolError as error:
            raise _refusal(error) from None
        return PoolSummaryResponse(id=saved.id, name=saved.name, is_default=saved.is_default)

    return router
