import hashlib
import hmac
import random
import secrets
from dataclasses import dataclass, field
from typing import Literal

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.pool import Topic
from devbingo_backend.prizes import Prize, satisfies
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


class ClaimNotValid(GameError):
    pass


class PrizeAlreadyAwarded(GameError):
    pass


@dataclass(frozen=True)
class HostLink:
    """The private handle on one game. Whoever holds it can control that game."""

    code: str
    token: str


@dataclass(frozen=True)
class PlayerRef:
    """One player in one game, addressed by the game's code and the player's display name."""

    code: str
    name: str


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


def _key(name: str) -> str:
    """The form a name is compared in: surrounding spaces and case are ignored."""
    return name.strip().casefold()


@dataclass
class _Game:
    host_token_hash: str
    status: Literal["lobby", "started"] = "lobby"
    # Display names, in the order players joined, as the lobby shows them.
    players: list[str] = field(default_factory=list)
    # Everything below is keyed by _key(name), so one player has one entry.
    tickets: dict[str, Ticket] = field(default_factory=dict)
    ticks: dict[str, set[str]] = field(default_factory=dict)
    connected: set[str] = field(default_factory=set)
    # The name each player was first given, for the lobby and for announcements.
    display_names: dict[str, str] = field(default_factory=dict)
    # The display name of the player each prize was awarded to. A prize is awarded at most once.
    awards: dict[Prize, str] = field(default_factory=dict)
    undrawn: list[Topic] = field(default_factory=list)
    draws: list[Draw] = field(default_factory=list)

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

    def join(self, player: PlayerRef) -> Ticket:
        """Join a game. A name held by a dropped player restores that player; a name held by
        a connected player is refused; any other name is a new join while the lobby is open.
        Names match without regard to case, so "Ada" and "ada" are the same player."""
        game = self._find(player.code)
        key = _key(player.name)
        if key in game.tickets:
            if key in game.connected:
                raise NameTaken(player.name)
            game.connected.add(key)
            return game.tickets[key]
        if game.status != "lobby":
            raise GameAlreadyStarted(player.code)
        if len(game.players) >= MAX_PLAYERS:
            raise GameFull(player.code)
        ticket = self._deal_unique_ticket(game)
        game.players.append(player.name.strip())
        game.tickets[key] = ticket
        game.ticks[key] = set()
        game.display_names[key] = player.name.strip()
        game.connected.add(key)
        return ticket

    def disconnect(self, player: PlayerRef) -> None:
        """The player has dropped. They keep their place and their ticks, and can rejoin by name."""
        game = self._find(player.code)
        key = _key(player.name)
        if key not in game.tickets:
            raise NotAPlayer(player.name)
        game.connected.discard(key)

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

    def tick(self, player: PlayerRef, topic_name: str) -> None:
        """Tick a topic on the player's ticket. It must be on the ticket and already drawn."""
        game, key, ticket_names = self._player_game(player)
        if topic_name not in ticket_names:
            raise TopicNotOnTicket(topic_name)
        if topic_name not in game.drawn_names():
            raise TopicNotDrawn(topic_name)
        game.ticks[key].add(topic_name)

    def untick(self, player: PlayerRef, topic_name: str) -> None:
        """Untick a topic on the player's ticket. Nothing blocks an untick until claims exist (issue 08)."""
        game, key, ticket_names = self._player_game(player)
        if topic_name not in ticket_names:
            raise TopicNotOnTicket(topic_name)
        game.ticks[key].discard(topic_name)

    def ticks(self, player: PlayerRef) -> frozenset[str]:
        """The topics this player has ticked."""
        game, key, _ = self._player_game(player)
        return frozenset(game.ticks[key])

    def claim(self, player: PlayerRef, prize: Prize) -> None:
        """Claim a prize. The claim is checked against what the player has ticked and what has
        been drawn. A valid claim awards the prize, which can be awarded only once a game."""
        game, key, _ = self._player_game(player)
        if game.status != "started":
            raise GameNotStarted(player.code)
        if prize in game.awards:
            raise PrizeAlreadyAwarded(prize)
        ticked_and_drawn = game.ticks[key] & game.drawn_names()
        if not satisfies(prize, ticked_and_drawn):
            raise ClaimNotValid(prize)
        game.awards[prize] = game.display_names[key]

    def prize_board(self, code: str) -> dict[Prize, str | None]:
        """Each prize and the player it was awarded to, or None while it is still open."""
        game = self._find(code)
        return {prize: game.awards.get(prize) for prize in Prize}

    def _player_game(self, player: PlayerRef) -> tuple[_Game, str, set[str]]:
        """The game, the player's key, and the topic names on their ticket. Refuses anyone not in the game."""
        game = self._find(player.code)
        key = _key(player.name)
        if key not in game.tickets:
            raise NotAPlayer(player.name)
        names = {
            cell.name
            for line in game.tickets[key].lines
            for cell in line
            if cell is not None
        }
        return game, key, names

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
