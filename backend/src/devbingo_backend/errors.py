"""The rule violations the engine reports. Each declares the wire code that tells a client why."""

from typing import ClassVar

from devbingo_backend.wire import ErrorCode


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
