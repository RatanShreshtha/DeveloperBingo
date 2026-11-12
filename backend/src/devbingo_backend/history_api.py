"""The public route for a finished game's history."""

from typing import Literal

from fastapi import APIRouter, HTTPException

from devbingo_backend.game import GameSummary
from devbingo_backend.history import HistoryStore, HistoryUnavailable
from devbingo_backend.wire import ClaimLogEntry, DrawAnnouncement, PrizeBoardEntry, _Message


class GameHistoryResponse(_Message):
    """A finished game: its draws in order, every claim with its outcome, and who won each prize."""

    code: str
    # Why it ended: the full house was awarded, or the host ended it.
    reason: Literal["full_house", "host"]
    pool_name: str | None
    draws: list[DrawAnnouncement]
    claims: list[ClaimLogEntry]
    winners: list[PrizeBoardEntry]

    @classmethod
    def from_summary(cls, summary: GameSummary) -> "GameHistoryResponse":
        return cls(
            code=summary.code,
            reason=summary.reason,
            pool_name=summary.pool_name,
            draws=[DrawAnnouncement.from_draw(draw) for draw in summary.draws],
            claims=[
                ClaimLogEntry(
                    player=c.player, prize=c.prize, accepted=c.accepted, error=c.error
                )
                for c in summary.claims
            ],
            winners=[
                PrizeBoardEntry(prize=prize, awarded_to=list(names))
                for prize, names in summary.winners.items()
            ],
        )


def history_router(store: HistoryStore) -> APIRouter:
    router = APIRouter()

    @router.get("/games/{code}/history", response_model=GameHistoryResponse)
    def read_game_history(code: str) -> GameHistoryResponse:
        """A finished game's record. Public: anyone with the game's code may read it."""
        try:
            summary = store.load(code)
        except HistoryUnavailable:
            raise HTTPException(status_code=503, detail="history unavailable") from None
        if summary is None:
            raise HTTPException(status_code=404, detail="no history for this game")
        return GameHistoryResponse.from_summary(summary)

    return router
