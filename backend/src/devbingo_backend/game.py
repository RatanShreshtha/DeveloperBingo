import hashlib
import hmac
import random
import secrets
from dataclasses import dataclass, field
from typing import Literal

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool import Topic
from devbingo_backend.ticket import Ticket, build_ticket

MAX_PLAYERS = 200

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 6


class GameError(Exception):
    """Base class for rule violations the engine reports to callers."""


class GameNotFound(GameError):
    pass


class NotHost(GameError):
    pass


class NameTaken(GameError):
    pass


class GameFull(GameError):
    pass


class GameAlreadyStarted(GameError):
    pass


class GameNotStarted(GameError):
    pass


class NoTopicsLeft(GameError):
    pass


@dataclass(frozen=True)
class CreatedGame:
    code: str
    host_token: str


@dataclass(frozen=True)
class Draw:
    position: int
    topic: Topic


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class _Game:
    host_token_hash: str
    status: Literal["lobby", "started"] = "lobby"
    players: list[str] = field(default_factory=list)
    tickets: dict[str, Ticket] = field(default_factory=dict)
    undrawn: list[Topic] = field(default_factory=list)
    draws: list[Draw] = field(default_factory=list)

    def is_new_ticket(self, candidate: Ticket) -> bool:
        """True when no player in this game already holds an identical ticket."""
        return all(candidate.lines != held.lines for held in self.tickets.values())


class GameRegistry:
    """In-memory store of live games. Holds all lobby and start rules."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._games: dict[str, _Game] = {}
        self._rng = rng or random.Random()

    def create_game(self) -> CreatedGame:
        code = self._new_code()
        host_token = secrets.token_urlsafe(24)
        self._games[code] = _Game(host_token_hash=_hash_token(host_token))
        return CreatedGame(code=code, host_token=host_token)

    def join(self, code: str, name: str) -> Ticket:
        game = self._find(code)
        if game.status != "lobby":
            raise GameAlreadyStarted(code)
        if name in game.players:
            raise NameTaken(name)
        if len(game.players) >= MAX_PLAYERS:
            raise GameFull(code)
        ticket = self._deal_unique_ticket(game)
        game.players.append(name)
        game.tickets[name] = ticket
        return ticket

    def _deal_unique_ticket(self, game: _Game) -> Ticket:
        while True:
            ticket = build_ticket(DEFAULT_POOL, self._rng)
            if game.is_new_ticket(ticket):
                return ticket

    def players(self, code: str) -> list[str]:
        """Names in the lobby. Public: every player in the room may see them."""
        return list(self._find(code).players)

    def lobby(self, code: str, host_token: str) -> list[str]:
        game = self._find(code)
        self._require_host(game, host_token)
        return list(game.players)

    def start(self, code: str, host_token: str) -> None:
        """Start the game: joining closes and the pool locks."""
        game = self._find(code)
        self._require_host(game, host_token)
        if game.status != "lobby":
            raise GameAlreadyStarted(code)
        game.status = "started"
        game.undrawn = list(DEFAULT_POOL.topics)

    def is_pool_locked(self, code: str) -> bool:
        """The pool locks when the game starts and stays locked."""
        return self._find(code).status == "started"

    def draw(self, code: str, host_token: str) -> Draw:
        """Draw one topic uniformly at random from those not yet drawn. Draws are final."""
        game = self._find(code)
        self._require_host(game, host_token)
        if game.status != "started":
            raise GameNotStarted(code)
        if not game.undrawn:
            raise NoTopicsLeft(code)
        topic = game.undrawn.pop(self._rng.randrange(len(game.undrawn)))
        draw = Draw(position=len(game.draws) + 1, topic=topic)
        game.draws.append(draw)
        return draw

    def draw_history(self, code: str) -> tuple[Draw, ...]:
        """Every draw so far, in order. Public: every player in the room may see them."""
        return tuple(self._find(code).draws)

    def _find(self, code: str) -> _Game:
        try:
            return self._games[code]
        except KeyError:
            raise GameNotFound(code) from None

    @staticmethod
    def _require_host(game: _Game, host_token: str) -> None:
        if not hmac.compare_digest(game.host_token_hash, _hash_token(host_token)):
            raise NotHost()

    def _new_code(self) -> str:
        while True:
            code = "".join(
                secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH)
            )
            if code not in self._games:
                return code
