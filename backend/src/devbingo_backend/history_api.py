"""The public route for an ended game's history."""

from fastapi import APIRouter, HTTPException

from devbingo_backend.history import HistoryStore, HistoryUnavailable
from devbingo_backend.wire import GameHistoryResponse


def history_router(store: HistoryStore) -> APIRouter:
    router = APIRouter()

    @router.get("/games/{code}/history", response_model=GameHistoryResponse)
    def read_game_history(code: str) -> GameHistoryResponse:
        """An ended game's record. Public: anyone with the game's code may read it."""
        try:
            summary = store.load(code)
        except HistoryUnavailable:
            raise HTTPException(status_code=503, detail="history unavailable") from None
        if summary is None:
            raise HTTPException(status_code=404, detail="no history for this game")
        return GameHistoryResponse.from_summary(summary)

    return router
