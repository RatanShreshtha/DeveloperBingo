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
    from devbingo_backend.pool import Pool


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
    # Sent to the host only: a settlement window opened or the last one closed.
    WINDOW_CHANGED = "window_changed"
    # Sent to one socket only: another socket took over its player with their rejoin token.
    REPLACED = "replaced"


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


class TopicResponse(_Message):
    name: str
    explanation: str


class PoolResponse(_Message):
    """A pool as columns of topics."""

    columns: list[list[TopicResponse]]

    @classmethod
    def from_pool(cls, pool: "Pool") -> "PoolResponse":
        return cls(
            columns=[
                [TopicResponse(name=topic.name, explanation=topic.explanation) for topic in column]
                for column in pool.columns()
            ]
        )


# What a client sends. Tick, untick and claim name no player: the socket's session does.


class JoinPayload(_Message):
    code: str
    name: str
    # Proves the sender is the player who joined before, so a reload can take the name over
    # while the old socket is still connected. Without it, a connected name is refused.
    rejoin_token: str | None = None


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


class GameSnapshot(_Message):
    """What a client needs to show a game from scratch: where it stands, who is in it, what has
    been drawn and who has been awarded what."""

    status: Literal["lobby", "started", "ended"]
    # Why the game ended. None while it has not.
    end_reason: Literal["full_house", "host"] | None
    players: list[str]
    draws: list[DrawAnnouncement]
    prizes: list[PrizeBoardEntry]


class JoinAck(GameSnapshot):
    """A player's snapshot: the game, plus their own ticket, ticks and pending claims."""

    ok: Literal[True] = True
    # The player's name as the game stored it on their first join. The client shows and keeps this
    # one, not what was typed, which may differ in case or spaces.
    name: str
    ticket: list[list[str | None]]
    ticks: list[str]
    # Prizes this player has claimed whose settlement window has not closed.
    pending_claims: list[Prize]
    # Kept private by the player. Every join issues a new one, replacing the last.
    rejoin_token: str


class WatchAck(GameSnapshot):
    """The host's snapshot: the game, plus the claim log, the pool and whether a window is open."""

    ok: Literal[True] = True
    claims: list[ClaimLogEntry]
    pool: PoolResponse
    # The name the pool was chosen under, if it has one.
    pool_name: str | None
    # True while a settlement window is open, so the host sees why a draw is refused.
    window_open: bool


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


class WindowChanged(_Message):
    """Whether any settlement window is open, which is why the server refuses draws."""

    open: bool


class Replaced(_Message):
    """Another socket took over this socket's player, which has left the game."""


# Models the OpenAPI schema carries that no REST route returns.
SOCKET_MODELS: list[type[BaseModel]] = [
    JoinPayload,
    TickPayload,
    ClaimPayload,
    PrizeBoardEntry,
    ClaimLogEntry,
    GameSnapshot,
    PoolResponse,
    TopicResponse,
    Refusal,
    Accepted,
    JoinAck,
    WatchAck,
    DrawAck,
    LobbyUpdated,
    GameStarted,
    GameEnded,
    PrizeAwarded,
    Replaced,
    WindowChanged,
]
