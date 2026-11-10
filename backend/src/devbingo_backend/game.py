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


class NotAPlayer(GameError):
    pass


class TopicNotDrawn(GameError):
    pass


class TopicNotOnTicket(GameError):
    pass


@dataclass(frozen=True)
class HostLink:
    """The private handle on one game. Whoever holds it can control that game."""

    code: str
    token: str


@dataclass(frozen=True)
class CreatedGame:
    code: str
    host_token: str

    @property
    def host_link(self) -> HostLink:
        return HostLink(code=self.code, token=self.host_token)


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
    ticks: dict[str, set[str]] = field(default_factory=dict)

    def drawn_names(self) -> set[str]:
        return {draw.topic.name for draw in self.draws}

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
        game.ticks[name] = set()
        return ticket

    def _deal_unique_ticket(self, game: _Game) -> Ticket:
        while True:
            ticket = build_ticket(DEFAULT_POOL, self._rng)
            if game.is_new_ticket(ticket):
                return ticket

    def players(self, code: str) -> list[str]:
        """Names in the lobby. Public: every player in the room may see them."""
        return list(self._find(code).players)

    def lobby(self, host: HostLink) -> list[str]:
        game = self._host_game(host)
        return list(game.players)

    def start(self, host: HostLink) -> None:
        """Start the game: joining closes and the pool locks."""
        game = self._host_game(host)
        if game.status != "lobby":
            raise GameAlreadyStarted(host.code)
        game.status = "started"
        game.undrawn = list(DEFAULT_POOL.topics)

    def is_pool_locked(self, code: str) -> bool:
        """The pool locks when the game starts and stays locked."""
        return self._find(code).status == "started"

    def draw(self, host: HostLink) -> Draw:
        """Draw one topic uniformly at random from those not yet drawn. Draws are final."""
        game = self._host_game(host)
        if game.status != "started":
            raise GameNotStarted(host.code)
        if not game.undrawn:
            raise NoTopicsLeft(host.code)
        topic = game.undrawn.pop(self._rng.randrange(len(game.undrawn)))
        draw = Draw(position=len(game.draws) + 1, topic=topic)
        game.draws.append(draw)
        return draw

    def draw_history(self, code: str) -> tuple[Draw, ...]:
        """Every draw so far, in order. Public: every player in the room may see them."""
        return tuple(self._find(code).draws)

    def tick(self, code: str, name: str, topic_name: str) -> frozenset[str]:
        """Tick a topic on the player's ticket. It must be on the ticket and already drawn."""
        game = self._find(code)
        ticket_names = self._ticket_names(game, name)
        if topic_name not in ticket_names:
            raise TopicNotOnTicket(topic_name)
        if topic_name not in game.drawn_names():
            raise TopicNotDrawn(topic_name)
        game.ticks[name].add(topic_name)
        return self.ticks(code, name)

    def untick(self, code: str, name: str, topic_name: str) -> frozenset[str]:
        """Untick a topic. Nothing stops a player unticking until claims exist (ticket 08)."""
        game = self._find(code)
        self._ticket_names(game, name)
        game.ticks[name].discard(topic_name)
        return self.ticks(code, name)

    def ticks(self, code: str, name: str) -> frozenset[str]:
        """The topics this player has ticked. Only the player's own ticks are returned."""
        return frozenset(self._find(code).ticks.get(name, set()))

    def _ticket_names(self, game: _Game, name: str) -> set[str]:
        if name not in game.tickets:
            raise NotAPlayer(name)
        return {
            cell.name
            for line in game.tickets[name].lines
            for cell in line
            if cell is not None
        }

    def _host_game(self, host: HostLink) -> _Game:
        """The game, once the link proves it belongs to its host."""
        game = self._find(host.code)
        if not hmac.compare_digest(game.host_token_hash, _hash_token(host.token)):
            raise NotHost()
        return game

    def _find(self, code: str) -> _Game:
        try:
            return self._games[code]
        except KeyError:
            raise GameNotFound(code) from None

    def _new_code(self) -> str:
        while True:
            code = "".join(
                secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LENGTH)
            )
            if code not in self._games:
                return code
