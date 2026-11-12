import hashlib
import hmac
import random
import secrets
from dataclasses import dataclass, field, replace
from typing import Literal

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.errors import (  # noqa: F401  (re-exported: callers import errors from here)
    AlreadyJoined,
    ClaimNotValid,
    GameAlreadyEnded,
    GameAlreadyStarted,
    GameError,
    GameFull,
    GameNotFound,
    GameNotStarted,
    InvalidMessage,
    NameTaken,
    NoTopicsLeft,
    NotAPlayer,
    NotHost,
    NotJoined,
    PrizeAlreadyAwarded,
    TopicNotDrawn,
    TopicNotOnTicket,
    UnknownPrize,
)
from devbingo_backend.names import name_key
from devbingo_backend.pool import Topic
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import Awarded, ClaimSettlement
from devbingo_backend.ticket import Ticket, build_ticket
from devbingo_backend.wire import HostLink

MAX_PLAYERS = 200

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 6


@dataclass(frozen=True)
class PlayerRef:
    """One player in one game, addressed by the game's code and the player's display name."""

    code: str
    name: str


@dataclass(frozen=True)
class Joined:
    """What a join did: the player's ticket, and whether they are new to the game or came back."""

    ticket: Ticket
    is_new_player: bool


@dataclass(frozen=True)
class Draw:
    position: int
    topic: Topic


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass
class _Player:
    """One player in a game: how the lobby shows them, their ticket, their ticks, and whether
    their socket is live."""

    name: str
    ticket: Ticket
    connected: bool = True
    ticks: set[str] = field(default_factory=set)


@dataclass
class _Game:
    host_token_hash: str
    status: Literal["lobby", "started", "ended"] = "lobby"
    # Keyed by name_key(name), so one player has one entry. In the order players joined.
    players: dict[str, _Player] = field(default_factory=dict)
    settlement: ClaimSettlement = field(default_factory=ClaimSettlement)
    undrawn: list[Topic] = field(default_factory=list)
    draws: list[Draw] = field(default_factory=list)

    def drawn_names(self) -> set[str]:
        return {draw.topic.name for draw in self.draws}

    def is_new_ticket(self, candidate: Ticket) -> bool:
        """True when no player in this game already holds an identical ticket."""
        return all(candidate.lines != held.ticket.lines for held in self.players.values())


class GameRegistry:
    """In-memory store of live games. Holds all lobby and start rules."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._games: dict[str, _Game] = {}
        self._rng = rng or random.Random()

    def create_game(self) -> HostLink:
        code = self._new_code()
        host_token = secrets.token_urlsafe(24)
        self._games[code] = _Game(host_token_hash=_hash_token(host_token))
        return HostLink(code=code, host_token=host_token)

    def join(self, player: PlayerRef) -> Joined:
        """Join a game. A name held by a dropped player restores that player; a name held by
        a connected player is refused; any other name is a new join while the lobby is open.
        Names match without regard to case, so "Ada" and "ada" are the same player."""
        game = self._find(player.code)
        self._refuse_if_ended(game, player.code)
        key = name_key(player.name)
        member = game.players.get(key)
        if member is not None:
            if member.connected:
                raise NameTaken(player.name)
            member.connected = True
            return Joined(member.ticket, is_new_player=False)
        if game.status != "lobby":
            raise GameAlreadyStarted(player.code)
        if len(game.players) >= MAX_PLAYERS:
            raise GameFull(player.code)
        ticket = self._deal_unique_ticket(game)
        game.players[key] = _Player(name=player.name.strip(), ticket=ticket)
        return Joined(ticket, is_new_player=True)

    def disconnect(self, player: PlayerRef) -> None:
        """The player has dropped. They keep their place and their ticks, and can rejoin by name."""
        game = self._find(player.code)
        member = game.players.get(name_key(player.name))
        if member is None:
            raise NotAPlayer(player.name)
        member.connected = False

    def _deal_unique_ticket(self, game: _Game) -> Ticket:
        while True:
            ticket = build_ticket(DEFAULT_POOL, self._rng)
            if game.is_new_ticket(ticket):
                return ticket

    def players(self, code: str) -> list[str]:
        """Names in the lobby. Public: every player in the room may see them."""
        return [member.name for member in self._find(code).players.values()]

    def lobby(self, host: HostLink) -> list[str]:
        """Names in the lobby, for the host. The same list as players(), after checking the host link."""
        self._host_game(host)
        return self.players(host.code)

    def start(self, host: HostLink) -> None:
        """Start the game: joining closes and the pool locks."""
        game = self._host_game(host)
        self._refuse_if_ended(game, host.code)
        if game.status != "lobby":
            raise GameAlreadyStarted(host.code)
        game.status = "started"
        game.undrawn = list(DEFAULT_POOL.topics)

    def end(self, host: HostLink) -> None:
        """The host ends the game, at any time. No draws or claims are accepted after it ends."""
        game = self._host_game(host)
        self._refuse_if_ended(game, host.code)
        self._finish(game)

    def is_pool_locked(self, code: str) -> bool:
        """The pool locks when the game starts and stays locked, including after it ends."""
        return self._find(code).status != "lobby"

    def draw(self, host: HostLink) -> Draw:
        """Draw one topic uniformly at random from those not yet drawn. Draws are final."""
        game = self._host_game(host)
        self._refuse_if_ended(game, host.code)
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
        game, member = self._player_game(player)
        if topic_name not in member.ticket.topic_names():
            raise TopicNotOnTicket(topic_name)
        if topic_name not in game.drawn_names():
            raise TopicNotDrawn(topic_name)
        member.ticks.add(topic_name)

    def untick(self, player: PlayerRef, topic_name: str) -> None:
        """Untick a topic on the player's ticket. Nothing blocks an untick yet: issue 12 refuses it
        while the player has a claim waiting in a settlement window."""
        _, member = self._player_game(player)
        if topic_name not in member.ticket.topic_names():
            raise TopicNotOnTicket(topic_name)
        member.ticks.discard(topic_name)

    def ticks(self, player: PlayerRef) -> frozenset[str]:
        """The topics this player has ticked."""
        _, member = self._player_game(player)
        return frozenset(member.ticks)

    def claim(self, player: PlayerRef, prize: Prize) -> Awarded:
        """Claim a prize. The claim is checked against what the player has ticked and what has
        been drawn. A valid claim awards the prize. Awarding the full house ends the game."""
        game, member = self._player_game(player)
        self._refuse_if_ended(game, player.code)
        if game.status != "started":
            raise GameNotStarted(player.code)
        ticked_and_drawn = member.ticks & game.drawn_names()
        awarded = game.settlement.claim(prize, member.name, member.ticket, ticked_and_drawn)
        if prize is Prize.FULL_HOUSE:
            self._finish(game)
            return replace(awarded, ends_game=True)
        return awarded

    def prize_board(self, code: str) -> dict[Prize, list[str]]:
        """Each prize and the names of the players it was awarded to. Empty while it is still open."""
        return self._find(code).settlement.board()

    @staticmethod
    def _refuse_if_ended(game: _Game, code: str) -> None:
        if game.status == "ended":
            raise GameAlreadyEnded(code)

    @staticmethod
    def _finish(game: _Game) -> None:
        """The one place a game ends, whether the host ended it or the full house was awarded."""
        game.status = "ended"

    def _player_game(self, player: PlayerRef) -> tuple[_Game, _Player]:
        """The game and the player's record. Refuses anyone not in the game."""
        game = self._find(player.code)
        member = game.players.get(name_key(player.name))
        if member is None:
            raise NotAPlayer(player.name)
        return game, member

    def _host_game(self, host: HostLink) -> _Game:
        """The game, once the link proves it belongs to its host."""
        game = self._find(host.code)
        if not hmac.compare_digest(game.host_token_hash, _hash_token(host.host_token)):
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
