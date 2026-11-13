import hashlib
import hmac
import logging
import random
import secrets
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

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
from devbingo_backend.scheduler import AsyncioScheduler, Scheduler
from devbingo_backend.settlement import ClaimRecord, ClaimSettlement, Evidence, Refused, Settled
from devbingo_backend.ticket import Ticket, build_ticket

MAX_PLAYERS = 200

# How long a settlement window stays open, unless the game registry is configured otherwise.
DEFAULT_WINDOW_SECONDS = 1.0

logger = logging.getLogger(__name__)

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 6


# Where a game stands.
GameStatus: TypeAlias = Literal["lobby", "started", "ended"]
# Why a game ended: the full house was awarded, or the host ended it.
EndReason: TypeAlias = Literal["full_house", "host"]


@dataclass(frozen=True)
class HostLink:
    """The private handle on one game: whoever holds it controls that game.

    It is what creating a game returns, and what every host command sends.
    """

    code: str
    host_token: str


@dataclass(frozen=True)
class PlayerRef:
    """One player in one game, addressed by the game's code and the player's display name."""

    code: str
    name: str


@dataclass(frozen=True)
class Outcome:
    """What a claim, the end of a game or a window's close changed, for the caller to announce.
    All three report in this one shape."""

    # Each window that closed: its prize, who it was awarded to, and every claim decided in it.
    settled: tuple[Settled, ...] = ()
    # Why the game ended, when this is what ended it.
    ended: EndReason | None = None
    # Whether any settlement window is open now. None when that did not change.
    window_open: bool | None = None
    # Claims decided the moment they arrived: refused outright. The host hears each; the claimant
    # is told by the claim's acknowledgement, so these never become `claim_settled`.
    decided: tuple[ClaimRecord, ...] = ()


@dataclass(frozen=True)
class ClaimResult:
    """What a claim did. `refusal` is why the claimant was refused at once, or None when the claim
    is waiting in a settlement window. Every refusal the host sees in the claim log is here, in
    `outcome.decided`; a claim from someone not in the game raises instead, since it is never logged."""

    outcome: Outcome
    refusal: GameError | None = None


# Hears the outcome of each window that closes on time, as no command is there to return it.
OutcomeListener = Callable[[str, Outcome], Awaitable[None]]


@dataclass(frozen=True)
class Draw:
    position: int
    topic: Topic


@dataclass(frozen=True)
class GameSnapshot:
    """Everything anyone in the game may see, enough to show it from scratch. Read-only: nothing
    here changes the game, and the game changing does not change it."""

    status: GameStatus
    # Why the game ended, or None while it has not.
    end_reason: EndReason | None
    # In the order players joined.
    players: tuple[str, ...]
    draws: tuple[Draw, ...]
    # Every prize, in the order of Prize, with the players it was awarded to (empty while open).
    prizes: Mapping[Prize, tuple[str, ...]]


@dataclass(frozen=True)
class PlayerSnapshot(GameSnapshot):
    """A player's Game snapshot: the game, plus their own ticket, ticks and claims."""

    # The player as the game knows them, with the name first stored.
    player: PlayerRef
    ticket: Ticket
    ticks: frozenset[str]
    # Prizes this player has claimed whose settlement window has not closed.
    pending_claims: tuple[Prize, ...]
    # This player's own decided claims, in the order they were decided.
    decided_claims: tuple[ClaimRecord, ...]


@dataclass(frozen=True)
class HostSnapshot(GameSnapshot):
    """The host's Game snapshot: the game, plus the claim log, the pool and the window state."""

    # Every decided claim, accepted or refused, in order. Only the host sees refusals.
    claims: tuple[ClaimRecord, ...]
    pool: Pool
    # The name the pool was chosen under, if it has one.
    pool_name: str | None
    # True while any settlement window is open, which is why draws are refused.
    window_open: bool


@dataclass(frozen=True)
class Joined:
    """What a join did: the player's snapshot, and whether they are new to the game or came back."""

    # Includes the player as the game knows them: callers address and compare them by this.
    snapshot: PlayerSnapshot
    is_new_player: bool
    # Private to the player. Showing it later proves they are the one who joined.
    rejoin_token: str
    # True when the player's name was still held by a live socket and this join took it over.
    took_over: bool = False


@dataclass(frozen=True)
class GameSummary:
    """An ended game as the History Store keeps it: the host's Game snapshot at the end, less what
    only a live game needs (the pool itself, the players, the window state). The game's code is its
    ID, and the fields carry the snapshot's names."""

    code: str
    end_reason: EndReason
    # The pool's name, when it has one.
    pool_name: str | None
    draws: tuple[Draw, ...]
    claims: tuple[ClaimRecord, ...]
    # Every prize, in the order of Prize, with the players it was awarded to (empty if unawarded).
    prizes: Mapping[Prize, tuple[str, ...]]


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
    status: GameStatus = "lobby"
    # Why the game ended: set when status becomes "ended".
    end_reason: EndReason | None = None
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
        scheduler: Scheduler | None = None,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        """`on_ended` is handed a summary of each game as it ends. It holds no networking or
        storage itself: the caller decides what to do with it.
        `code_taken` says whether a code is already in use somewhere the registry cannot see, such
        as stored history, so a new game never reuses it.
        Each settlement window closes `window_seconds` after it opens, through `scheduler`."""
        self._games: dict[str, _Game] = {}
        self._rng = rng or random.Random()
        self._on_ended = on_ended
        self._code_taken = code_taken
        self._scheduler = scheduler or AsyncioScheduler()
        self._window_seconds = window_seconds
        self._on_outcome: OutcomeListener | None = None

    def listen(self, on_outcome: OutcomeListener) -> None:
        """Hand the outcome of every window that closes on time to `on_outcome`. Commands return
        their outcomes; a timed close has no caller, so it is reported here. One listener."""
        self._on_outcome = on_outcome

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
                self._player_snapshot(game, member),
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
        return Joined(
            self._player_snapshot(game, member),
            is_new_player=True,
            rejoin_token=self._issue_token(member),
        )

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

    def start(self, host: HostLink) -> None:
        """Start the game: joining closes and the pool locks."""
        game = self._host_game(host)
        self._refuse_if_ended(game, host.code)
        if game.status != "lobby":
            raise GameAlreadyStarted(host.code)
        game.status = "started"
        game.undrawn = list(game.pool.topics)

    def end(self, host: HostLink) -> Outcome:
        """The host ends the game, at any time. No draws or claims are accepted after it ends.
        Every open settlement window settles at once, its claims refused as `game_ended`. A close
        still scheduled for one of them later finds it gone and does nothing."""
        game = self._host_game(host)
        self._refuse_if_ended(game, host.code)
        was_open = game.settlement.window_open()
        refusal = GameAlreadyEnded(host.code)
        settled = tuple(
            outcome
            for prize in game.settlement.open_prizes()
            if (outcome := game.settlement.close(prize, self._evidence(game), refusal)) is not None
        )
        self._end(game, "host")
        return Outcome(settled, ended="host", window_open=False if was_open else None)

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

    def claim(self, player: PlayerRef, prize: Prize) -> ClaimResult:
        """Claim a prize. A claim the game cannot take is refused at once: the result carries the
        refusal, and the claim is logged for the host. A valid one waits in the prize's settlement window,
        opening it if none is; the window closes on its own after the window length, and its
        outcome goes to the listener. A repeat while the window is open changes nothing."""
        game, member = self._player_game(player)
        was_open = game.settlement.window_open()
        ticked_and_drawn = member.ticks & game.drawn_names()
        decision = game.settlement.claim(
            prize, member.name, member.ticket, ticked_and_drawn, self._game_refusal(game, player.code)
        )
        if isinstance(decision, Refused):
            return ClaimResult(Outcome(decided=(decision.record,)), decision.error)
        if decision.opened_window:
            self._scheduler.call_later(
                self._window_seconds, lambda: self._close_on_time(player.code, prize)
            )
        return ClaimResult(Outcome(window_open=True if not was_open else None))

    async def _close_on_time(self, code: str, prize: Prize) -> None:
        outcome = self._close_window(code, prize)
        if outcome is not None and self._on_outcome is not None:
            await self._on_outcome(code, outcome)

    def _close_window(self, code: str, prize: Prize) -> Outcome | None:
        """Close the prize's settlement window now: every claim in it is judged against the draws,
        and all that earn the prize win it together. Awarding the full house ends the game.
        Returns None when no window is open for the prize, as when the game ended first. Only the
        clock calls this: tests fire the scheduler they gave the registry."""
        game = self._find(code)
        refusal = GameAlreadyEnded(code) if game.status == "ended" else None
        settled = game.settlement.close(prize, self._evidence(game), refusal)
        if settled is None:
            return None
        ended: EndReason | None = None
        if settled.awarded_to and prize is Prize.FULL_HOUSE:
            self._end(game, "full_house")
            ended = "full_house"
        window_open = None if game.settlement.window_open() else False
        return Outcome((settled,), ended=ended, window_open=window_open)

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

    def player_snapshot(self, player: PlayerRef) -> PlayerSnapshot:
        """The player's Game snapshot. Refuses anyone not in the game."""
        game, member = self._player_game(player)
        return self._player_snapshot(game, member)

    def host_snapshot(self, host: HostLink) -> HostSnapshot:
        """The host's Game snapshot, once the link proves it belongs to the game's host."""
        return self._host_snapshot_of(self._host_game(host))

    @classmethod
    def _host_snapshot_of(cls, game: _Game) -> HostSnapshot:
        """The one place the host's view of a game is assembled: for the host, and for the
        summary kept when the game ends."""
        return HostSnapshot(
            **cls._shared(game),
            claims=tuple(game.settlement.log()),
            pool=game.pool,
            pool_name=game.pool_name,
            window_open=game.settlement.window_open(),
        )

    def _player_snapshot(self, game: _Game, member: _Player) -> PlayerSnapshot:
        return PlayerSnapshot(
            **self._shared(game),
            player=PlayerRef(game.code, member.name),
            ticket=member.ticket,
            ticks=frozenset(member.ticks),
            pending_claims=tuple(game.settlement.pending_prizes(member.name)),
            decided_claims=tuple(
                record for record in game.settlement.log() if record.player == member.name
            ),
        )

    @staticmethod
    def _shared(game: _Game) -> dict[str, Any]:
        """The parts of a snapshot everyone gets."""
        return {
            "status": game.status,
            "end_reason": game.end_reason,
            "players": tuple(member.name for member in game.players.values()),
            "draws": tuple(game.draws),
            "prizes": MappingProxyType(
                {prize: tuple(names) for prize, names in game.settlement.board().items()}
            ),
        }

    @staticmethod
    def _refuse_if_ended(game: _Game, code: str) -> None:
        if game.status == "ended":
            raise GameAlreadyEnded(code)

    def _end(self, game: _Game, reason: EndReason) -> None:
        """The one place a game ends, whether the host ended it or the full house was awarded.
        A failing observer is logged: it never stops the game from ending."""
        game.status = "ended"
        game.end_reason = reason
        if self._on_ended is None:
            return
        snapshot = self._host_snapshot_of(game)
        summary = GameSummary(
            code=game.code,
            end_reason=reason,
            pool_name=snapshot.pool_name,
            draws=snapshot.draws,
            claims=snapshot.claims,
            prizes=snapshot.prizes,
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
