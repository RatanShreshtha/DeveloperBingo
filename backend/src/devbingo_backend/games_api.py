"""The route that creates a game."""

from fastapi import APIRouter

from devbingo_backend.game import GameRegistry, HostLink
from devbingo_backend.pool_library import DEFAULT_POOL_NAME, PoolLibrary
from devbingo_backend.wire import CreateGameRequest


def build_games_router(registry: GameRegistry, library: PoolLibrary) -> APIRouter:
    router = APIRouter()

    @router.post("/games", status_code=201, response_model=HostLink)
    def create_game(body: CreateGameRequest | None = None) -> HostLink:
        """Create a game on the default pool, or on the saved pool named by `pool_id`."""
        if body is None or body.pool_id is None:
            return registry.create_game(
                library.load_default(), pool_name=DEFAULT_POOL_NAME
            )
        saved = library.get(body.pool_id)
        return registry.create_game(saved.pool, pool_name=saved.name)

    return router
