"""The shapes the server sends to clients, typed once.

These models appear in the OpenAPI schema, so the frontend generates its
types from them rather than writing them by hand.
"""

from pydantic import BaseModel

from devbingo_backend.game import Draw


class DrawAnnouncement(BaseModel):
    """A draw as players see it: its place in the game, the topic and its explanation."""

    position: int
    name: str
    explanation: str

    @classmethod
    def from_draw(cls, draw: Draw) -> "DrawAnnouncement":
        return cls(
            position=draw.position,
            name=draw.topic.name,
            explanation=draw.topic.explanation,
        )


class DrawHistoryResponse(BaseModel):
    draws: list[DrawAnnouncement]
