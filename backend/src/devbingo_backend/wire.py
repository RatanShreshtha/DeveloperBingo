"""Every message that crosses the wire, typed once.

The models here cover the REST responses and every socket payload, acknowledgement
and event. They all appear in the OpenAPI schema, so the frontend generates its
types from them rather than writing them by hand.
"""

from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from devbingo_backend.prizes import Prize

if TYPE_CHECKING:
    from devbingo_backend.game import Draw


class ErrorCode(StrEnum):
    """Why a request was refused. Each engine error declares the code it maps to."""

    NOT_FOUND = "not_found"
    NOT_HOST = "not_host"
    NAME_TAKEN = "name_taken"
    GAME_FULL = "game_full"
    ALREADY_STARTED = "already_started"
    GAME_ENDED = "game_ended"
    NOT_STARTED = "not_started"
    NO_TOPICS_LEFT = "no_topics_left"
    NOT_A_PLAYER = "not_a_player"
    NOT_DRAWN = "not_drawn"
    NOT_ON_TICKET = "not_on_ticket"
    CLAIM_NOT_VALID = "claim_not_valid"
    PRIZE_TAKEN = "prize_taken"
    ALREADY_JOINED = "already_joined"
    NOT_JOINED = "not_joined"
    UNKNOWN_PRIZE = "unknown_prize"
    INVALID_MESSAGE = "invalid_message"
    SETTLEMENT_OPEN = "settlement_open"
    CLAIM_PENDING = "claim_pending"


class ClientEvent(StrEnum):
    """The events a client sends to the server."""

    JOIN_GAME = "join_game"
    WATCH_LOBBY = "watch_lobby"
    START_GAME = "start_game"
    DRAW_TOPIC = "draw_topic"
    END_GAME = "end_game"
    TICK_TOPIC = "tick_topic"
    UNTICK_TOPIC = "untick_topic"
    CLAIM_PRIZE = "claim_prize"


class ServerEvent(StrEnum):
    """The events the server announces to a room."""

    LOBBY_UPDATED = "lobby_updated"
    GAME_STARTED = "game_started"
    GAME_ENDED = "game_ended"
    TOPIC_DRAWN = "topic_drawn"
    PRIZE_AWARDED = "prize_awarded"
    # Sent to the host only: refused claims stay private to the claimant among players.
    CLAIM_LOGGED = "claim_logged"


class _Message(BaseModel):
    # Fields with a default (like `ok`) are always sent, so the schema marks them required.
    model_config = ConfigDict(json_schema_serialization_defaults_required=True)


class HostLink(_Message):
    """The private handle on one game: whoever holds it controls that game.

    It is what creating a game returns, and what every host command sends.
    """

    model_config = ConfigDict(frozen=True, json_schema_serialization_defaults_required=True)

    code: str
    host_token: str


class DrawAnnouncement(_Message):
    """A draw as players see it: its place in the game, the topic and its explanation."""

    position: int
    name: str
    explanation: str

    @classmethod
    def from_draw(cls, draw: "Draw") -> "DrawAnnouncement":
        return cls(
            position=draw.position,
            name=draw.topic.name,
            explanation=draw.topic.explanation,
        )


class DrawHistoryResponse(_Message):
    draws: list[DrawAnnouncement]


# What a client sends. Tick, untick and claim name no player: the socket's session does.


class JoinPayload(_Message):
    code: str
    name: str


class TickPayload(_Message):
    topic: str


class ClaimPayload(_Message):
    # A plain string so that an unknown prize is refused as `unknown_prize`, not as a bad message.
    prize: str


# What the server answers.


class PrizeBoardEntry(_Message):
    """One prize, and the names of the players it was awarded to. Empty while it is open."""

    prize: Prize
    awarded_to: list[str]


class ClaimLogEntry(_Message):
    """One decided claim as the host sees it. A refused claim says why, as a wire error code."""

    player: str
    prize: Prize
    accepted: bool
    error: ErrorCode | None


class Refusal(_Message):
    ok: Literal[False] = False
    error: ErrorCode


class Accepted(_Message):
    ok: Literal[True] = True


class JoinAck(_Message):
    ok: Literal[True] = True
    ticket: list[list[str | None]]
    ticks: list[str]
    prizes: list[PrizeBoardEntry]


class WatchAck(_Message):
    ok: Literal[True] = True
    players: list[str]
    prizes: list[PrizeBoardEntry]
    claims: list[ClaimLogEntry]


class DrawAck(_Message):
    ok: Literal[True] = True
    draw: DrawAnnouncement


# What the server announces to a room.


class LobbyUpdated(_Message):
    players: list[str]


class GameStarted(_Message):
    pass


class GameEnded(_Message):
    """The game is over: someone claimed the full house, or the host ended it."""

    reason: Literal["full_house", "host"]


class PrizeAwarded(_Message):
    prize: Prize
    awarded_to: list[str]


# Models the OpenAPI schema carries that no REST route returns.
SOCKET_MODELS: list[type[BaseModel]] = [
    JoinPayload,
    TickPayload,
    ClaimPayload,
    PrizeBoardEntry,
    ClaimLogEntry,
    Refusal,
    Accepted,
    JoinAck,
    WatchAck,
    DrawAck,
    LobbyUpdated,
    GameStarted,
    GameEnded,
    PrizeAwarded,
]
