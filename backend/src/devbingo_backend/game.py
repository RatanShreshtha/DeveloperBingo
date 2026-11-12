import hashlib
import hmac
import logging
import random
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Literal

from devbingo_backend.errors import (  # noqa: F401  (re-exported: callers import errors from here)
    AlreadyJoined,
    ClaimNotValid,
    ClaimPending,
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
    SettlementWindowOpen,
    TopicNotDrawn,
    TopicNotOnTicket,
    UnknownPrize,
)
from devbingo_backend.names import name_key
from devbingo_backend.pool import Pool, Topic
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord, ClaimSettlement, Evidence, Pending, Settled
from devbingo_backend.ticket import Ticket, build_ticket
from devbingo_backend.wire import HostLink

MAX_PLAYERS = 200

logger = logging.getLogger(__name__)

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
    # Private to the player. Showing it later proves they are the one who joined.
    rejoin_token: str
    # True when the player's name was still held by a live socket and this join took it over.
    took_over: bool = False


@dataclass(frozen=True)
class Draw:
    position: int
    topic: Topic


@dataclass(frozen=True)
class GameSummary:
    """An ended game as the History Store keeps it. The game's code is its ID."""

    code: str
    reason: Literal["full_house", "host"]
    # The pool's name, when it has one.
    pool_name: str | None
    draws: tuple[Draw, ...]
    claims: tuple[ClaimRecord, ...]
    # Every prize, in the order of Prize, with the players it was awarded to (empty if unawarded).
    winners: dict[Prize, tuple[str, ...]]


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
    # Hash of the token the player last joined with. Replaced by every join.
    token_hash: str = ""


@dataclass
class _Game:
    code: str
    host_token_hash: str
    # Fixed from creation: tickets are dealt from it as players join, so it can't change.
    pool: Pool
    pool_name: str | None = None
    status: Literal["lobby", "started", "ended"] = "lobby"
    # Why the game ended: set when status becomes "ended".
    end_reason: Literal["full_house", "host"] | None = None
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

    def __init__(
        self,
        rng: random.Random | None = None,
        on_ended: Callable[[GameSummary], None] | None = None,
        code_taken: Callable[[str], bool] | None = None,
    ) -> None:
        """`on_ended` is handed a summary of each game as it ends. It holds no networking or
        storage itself: the caller decides what to do with it.
        `code_taken` says whether a code is already in use somewhere the registry cannot see, such
        as stored history, so a new game never reuses it."""
        self._games: dict[str, _Game] = {}
        self._rng = rng or random.Random()
        self._on_ended = on_ended
        self._code_taken = code_taken

    def create_game(self, pool: Pool, pool_name: str | None = None) -> HostLink:
        code = self._new_code()
        host_token = secrets.token_urlsafe(24)
        self._games[code] = _Game(
            code=code, host_token_hash=_hash_token(host_token), pool=pool, pool_name=pool_name
        )
        return HostLink(code=code, host_token=host_token)

    def join(self, player: PlayerRef, rejoin_token: str | None = None) -> Joined:
        """Join a game. A name held by a dropped player restores that player, also after the game
        has ended so they can read its result; a name held by a connected player is refused unless
        the join shows that player's rejoin token, which takes the name over; any other name is a
        new join while the lobby is open. Names match without regard to case, so "Ada" and "ada"
        are the same player. Every join issues a fresh rejoin token."""
        game = self._find(player.code)
        key = name_key(player.name)
        member = game.players.get(key)
        if member is not None:
            holds_token = (
                rejoin_token is not None
                and bool(member.token_hash)
                and hmac.compare_digest(member.token_hash, _hash_token(rejoin_token))
            )
            if member.connected and not holds_token:
                raise NameTaken(player.name)
            took_over = member.connected
            member.connected = True
            return Joined(
                member.ticket,
                is_new_player=False,
                rejoin_token=self._issue_token(member),
                took_over=took_over,
            )
        self._refuse_if_ended(game, player.code)
        if game.status != "lobby":
            raise GameAlreadyStarted(player.code)
        if len(game.players) >= MAX_PLAYERS:
            raise GameFull(player.code)
        ticket = self._deal_unique_ticket(game)
        member = _Player(name=player.name.strip(), ticket=ticket)
        game.players[key] = member
        return Joined(ticket, is_new_player=True, rejoin_token=self._issue_token(member))

    @staticmethod
    def _issue_token(member: _Player) -> str:
        token = secrets.token_urlsafe(24)
        member.token_hash = _hash_token(token)
        return token

    def disconnect(self, player: PlayerRef) -> None:
        """The player has dropped. They keep their place and their ticks, and can rejoin by name."""
        game = self._find(player.code)
        member = game.players.get(name_key(player.name))
        if member is None:
            raise NotAPlayer(player.name)
        member.connected = False

    def _deal_unique_ticket(self, game: _Game) -> Ticket:
        while True:
            ticket = build_ticket(game.pool, self._rng)
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
        game.undrawn = list(game.pool.topics)

    def end(self, host: HostLink) -> tuple[Settled, ...]:
        """The host ends the game, at any time. No draws or claims are accepted after it ends.
        Every open settlement window settles at once, its claims refused as `game_ended`; the
        outcomes are returned so the caller can answer the claimants."""
        game = self._host_game(host)
        self._refuse_if_ended(game, host.code)
        refusal = GameAlreadyEnded(host.code)
        settled = tuple(
            outcome
            for prize in game.settlement.open_prizes()
            if (outcome := game.settlement.close(prize, self._evidence(game), refusal)) is not None
        )
        self._end(game, "host")
        return settled

    def draw(self, host: HostLink) -> Draw:
        """Draw one topic uniformly at random from those not yet drawn. Draws are final.
        Draws are held while any settlement window is open."""
        game = self._host_game(host)
        self._refuse_if_ended(game, host.code)
        if game.settlement.window_open():
            raise SettlementWindowOpen(host.code)
        if game.status != "started":
            raise GameNotStarted(host.code)
        if not game.undrawn:
            raise NoTopicsLeft(host.code)
        topic = game.undrawn.pop(self._rng.randrange(len(game.undrawn)))
        draw = Draw(position=len(game.draws) + 1, topic=topic)
        game.draws.append(draw)
        return draw

    def pool_of(self, code: str) -> Pool:
        """The pool this game was created with. Public: it is fixed for the life of the game."""
        return self._find(code).pool

    def pool_name_of(self, code: str) -> str | None:
        """The name of the pool this game was created with, if it has one. Public, like the pool."""
        return self._find(code).pool_name

    def draw_history(self, code: str) -> tuple[Draw, ...]:
        """Every draw so far, in order. Public: every player in the room may see them."""
        return tuple(self._find(code).draws)

    def tick(self, player: PlayerRef, topic_name: str) -> None:
        """Tick a topic on the player's ticket. It must be on the ticket and already drawn.
        Refused once the game has ended: the ticks then match the claims that were judged."""
        game, member = self._player_game(player)
        self._refuse_if_ended(game, player.code)
        if topic_name not in member.ticket.topic_names():
            raise TopicNotOnTicket(topic_name)
        if topic_name not in game.drawn_names():
            raise TopicNotDrawn(topic_name)
        member.ticks.add(topic_name)

    def untick(self, player: PlayerRef, topic_name: str) -> None:
        """Untick a topic on the player's ticket. Refused while the player has a claim waiting in a
        settlement window: a player may untick only before a claim is made."""
        game, member = self._player_game(player)
        self._refuse_if_ended(game, player.code)
        if game.settlement.has_pending(member.name):
            raise ClaimPending(topic_name)
        if topic_name not in member.ticket.topic_names():
            raise TopicNotOnTicket(topic_name)
        member.ticks.discard(topic_name)

    def ticks(self, player: PlayerRef) -> frozenset[str]:
        """The topics this player has ticked."""
        _, member = self._player_game(player)
        return frozenset(member.ticks)

    def claim(self, player: PlayerRef, prize: Prize) -> Pending:
        """Claim a prize. A claim the ticket does not earn is refused at once. A valid one waits in
        the prize's settlement window, which it opens if none is; nothing is awarded until
        `close_window`. The outcome says whether this claim opened the window."""
        game, member = self._player_game(player)
        ticked_and_drawn = member.ticks & game.drawn_names()
        return game.settlement.claim(
            prize, member.name, member.ticket, ticked_and_drawn, self._game_refusal(game, player.code)
        )

    def close_window(self, code: str, prize: Prize) -> Settled | None:
        """Close the prize's settlement window: every claim in it is judged against the draws now,
        and all that earn the prize win it together. Awarding the full house ends the game.
        Returns None when no window is open for the prize."""
        game = self._find(code)
        refusal = GameAlreadyEnded(code) if game.status == "ended" else None
        settled = game.settlement.close(prize, self._evidence(game), refusal)
        if settled is not None and settled.awarded_to and prize is Prize.FULL_HOUSE:
            self._end(game, "full_house")
            return replace(settled, ends_game=True)
        return settled

    @staticmethod
    def _evidence(game: _Game) -> Evidence:
        def evidence(name: str) -> tuple[Ticket, set[str]]:
            member = game.players[name_key(name)]
            return member.ticket, member.ticks & game.drawn_names()

        return evidence

    @staticmethod
    def _game_refusal(game: _Game, code: str) -> GameError | None:
        if game.status == "ended":
            return GameAlreadyEnded(code)
        if game.status != "started":
            return GameNotStarted(code)
        return None

    def status(self, code: str) -> Literal["lobby", "started", "ended"]:
        """Where the game stands. Public."""
        return self._find(code).status

    def end_reason(self, code: str) -> Literal["full_house", "host"] | None:
        """Why the game ended, or None while it has not. Public."""
        return self._find(code).end_reason

    def pending_claims(self, player: PlayerRef) -> list[Prize]:
        """The prizes this player has claimed whose settlement window is still open."""
        game, member = self._player_game(player)
        return game.settlement.pending_prizes(member.name)

    def window_open(self, code: str) -> bool:
        """True while any settlement window is open in the game."""
        return self._find(code).settlement.window_open()

    def prize_board(self, code: str) -> dict[Prize, list[str]]:
        """Each prize and the names of the players it was awarded to. Empty while it is still open."""
        return self._find(code).settlement.board()

    def claim_log(self, code: str) -> list[ClaimRecord]:
        """Every claim decided so far, accepted or refused, in order. For the host only: a refused
        claim is private to the claimant among players."""
        return self._find(code).settlement.log()

    @staticmethod
    def _refuse_if_ended(game: _Game, code: str) -> None:
        if game.status == "ended":
            raise GameAlreadyEnded(code)

    def _end(self, game: _Game, reason: Literal["full_house", "host"]) -> None:
        """The one place a game ends, whether the host ended it or the full house was awarded.
        A failing observer is logged: it never stops the game from ending."""
        game.status = "ended"
        game.end_reason = reason
        if self._on_ended is None:
            return
        summary = GameSummary(
            code=game.code,
            reason=reason,
            pool_name=game.pool_name,
            draws=tuple(game.draws),
            claims=tuple(game.settlement.log()),
            winners={prize: tuple(names) for prize, names in game.settlement.board().items()},
        )
        try:
            self._on_ended(summary)
        except Exception:
            logger.exception("could not hand over the summary of game %s", game.code)

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
            if code not in self._games and not (self._code_taken and self._code_taken(code)):
                return code
