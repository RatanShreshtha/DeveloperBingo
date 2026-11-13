"""The rule violations the engine reports. Each declares the wire code that tells a client why."""

from enum import StrEnum
from typing import ClassVar


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


class GameError(Exception):
    """Base class for rule violations the engine reports to callers.

    Each subclass declares the wire code that tells a client why it was refused.
    """

    code: ClassVar[ErrorCode]


class GameNotFound(GameError):
    code = ErrorCode.NOT_FOUND


class NotHost(GameError):
    code = ErrorCode.NOT_HOST


class NameTaken(GameError):
    code = ErrorCode.NAME_TAKEN


class GameFull(GameError):
    code = ErrorCode.GAME_FULL


class GameAlreadyStarted(GameError):
    code = ErrorCode.ALREADY_STARTED


class GameAlreadyEnded(GameError):
    code = ErrorCode.GAME_ENDED


class GameNotStarted(GameError):
    code = ErrorCode.NOT_STARTED


class NoTopicsLeft(GameError):
    code = ErrorCode.NO_TOPICS_LEFT


class NotAPlayer(GameError):
    code = ErrorCode.NOT_A_PLAYER


class TopicNotDrawn(GameError):
    code = ErrorCode.NOT_DRAWN


class TopicNotOnTicket(GameError):
    code = ErrorCode.NOT_ON_TICKET


class ClaimNotValid(GameError):
    code = ErrorCode.CLAIM_NOT_VALID


class PrizeAlreadyAwarded(GameError):
    code = ErrorCode.PRIZE_TAKEN


class AlreadyJoined(GameError):
    code = ErrorCode.ALREADY_JOINED


class NotJoined(GameError):
    code = ErrorCode.NOT_JOINED


class UnknownPrize(GameError):
    code = ErrorCode.UNKNOWN_PRIZE


class InvalidMessage(GameError):
    """A message that is missing a field, or has one of the wrong type."""

    code = ErrorCode.INVALID_MESSAGE


class SettlementWindowOpen(GameError):
    """A draw was asked for while a settlement window is open: draws are held until it closes."""

    code = ErrorCode.SETTLEMENT_OPEN


class ClaimPending(GameError):
    """A tick was taken back while the player has a claim waiting in a settlement window."""

    code = ErrorCode.CLAIM_PENDING
