from collections.abc import Callable, Set
from dataclasses import dataclass, field

from devbingo_backend.errors import (
    ClaimNotValid,
    ErrorCode,
    GameError,
    PrizeAlreadyAwarded,
)
from devbingo_backend.prizes import Prize, prizes_earned
from devbingo_backend.ticket import Ticket


@dataclass(frozen=True)
class Pending:
    """A claim waiting in a settlement window. `opened_window` is true when this claim opened the
    prize's window, so the caller knows to schedule the close. `window` is the game-wide change:
    True when this claim opened the first window of the game, None when no window changed state."""

    prize: Prize
    opened_window: bool
    window: bool | None = None


@dataclass(frozen=True)
class Refused:
    """A claim refused at once. It is already in the claim log: `record` is its entry, and `error`
    is why, for the claimant."""

    record: "ClaimRecord"
    error: GameError


@dataclass(frozen=True)
class Settled:
    """A closed window: every player the prize is now awarded to, and the claimants refused at close."""

    prize: Prize
    awarded_to: tuple[str, ...]
    refused: tuple[str, ...] = ()
    # What was decided for each claimant at close, in the order they claimed.
    records: tuple["ClaimRecord", ...] = ()
    # The game-wide change this close made: False when it closed the game's last open window,
    # None when other windows are still open or none was.
    window: bool | None = None


# What a claimant has, looked up when a window closes: their ticket, and the topics both ticked and drawn.
Evidence = Callable[[str], tuple[Ticket, Set[str]]]


@dataclass(frozen=True)
class ClaimRecord:
    """One decided claim, as the host sees it. A refused claim carries the wire code that says why."""

    player: str
    prize: Prize
    accepted: bool
    error: ErrorCode | None = None


@dataclass
class ClaimSettlement:
    """Judges claims for one game and holds who each prize was awarded to.

    The first valid claim for a prize opens a settlement window; claims arriving while it is open
    wait, and all are judged when `close` is called. There is no clock here: the caller closes the
    window. A prize can hold several players, since simultaneous claims win it together.
    A claim is logged when it is decided: at once if refused outright, otherwise at close.
    """

    _awards: dict[Prize, list[str]] = field(default_factory=dict)
    # The claimants waiting in each open window, in the order they claimed.
    _windows: dict[Prize, list[str]] = field(default_factory=dict)
    _log: list[ClaimRecord] = field(default_factory=list)

    def claim(
        self,
        prize: Prize,
        claimant: str,
        ticket: Ticket,
        ticked_and_drawn: Set[str],
        refusal: GameError | None = None,
    ) -> Pending | Refused:
        """Take a claim. It is refused at once, and logged, if the game broke a rule (`refusal`),
        the prize is already awarded, or no window is open and the ticket does not earn it.
        Otherwise it waits in the prize's window, opening it if none is. A repeat by the same
        player is the same result."""
        was_open = self.window_open()
        waiting = self._windows.get(prize)
        try:
            if refusal is not None:
                raise refusal
            if prize in self._awards:
                raise PrizeAlreadyAwarded(prize)
            if waiting is None and prize not in prizes_earned(ticket, ticked_and_drawn):
                raise ClaimNotValid(prize)
        except GameError as err:
            return Refused(self._decide(claimant, prize, err), err)
        if waiting is None:
            self._windows[prize] = [claimant]
            return Pending(prize, opened_window=True, window=self._transition(was_open))
        if claimant not in waiting:
            waiting.append(claimant)
        return Pending(prize, opened_window=False, window=self._transition(was_open))

    def close(
        self, prize: Prize, evidence: Evidence, refusal: GameError | None = None
    ) -> Settled | None:
        """Close the prize's window: judge every waiting claim and award the prize to those that
        earn it. Does nothing when no window is open. `refusal` refuses every waiting claim."""
        was_open = self.window_open()
        waiting = self._windows.pop(prize, None)
        if waiting is None:
            return None
        winners: list[str] = []
        refused: list[str] = []
        records: list[ClaimRecord] = []
        for claimant in waiting:
            error = refusal
            if error is None:
                ticket, ticked_and_drawn = evidence(claimant)
                if prize not in prizes_earned(ticket, ticked_and_drawn):
                    error = ClaimNotValid(prize)
            records.append(self._decide(claimant, prize, error))
            (refused if error else winners).append(claimant)
        if winners:
            self._awards[prize] = winners
        return Settled(
            prize,
            tuple(winners),
            tuple(refused),
            tuple(records),
            window=self._transition(was_open),
        )

    def close_all(
        self, evidence: Evidence, refusal: GameError | None = None
    ) -> tuple[tuple[Settled, ...], bool | None]:
        """Close every open window, as the game ends. Returns what each close reported, and the
        game-wide window change over the whole call: False when windows were open and now none are."""
        was_open = self.window_open()
        settled = tuple(
            outcome
            for prize in list(self._windows)
            if (outcome := self.close(prize, evidence, refusal)) is not None
        )
        return settled, self._transition(was_open)

    def window_open(self) -> bool:
        """True while any prize has a settlement window open."""
        return bool(self._windows)

    def _transition(self, was_open: bool) -> bool | None:
        """The game-wide window change since `was_open`: True when a window opened, False when the
        last one closed, None when that did not change."""
        now = self.window_open()
        return now if now != was_open else None

    def has_pending(self, claimant: str) -> bool:
        """True when the player has a claim waiting in an open window."""
        return any(claimant in waiting for waiting in self._windows.values())

    def pending_prizes(self, claimant: str) -> list[Prize]:
        """The prizes the player has a claim waiting on, in the order of Prize."""
        return [prize for prize in Prize if claimant in self._windows.get(prize, [])]

    def _decide(
        self, claimant: str, prize: Prize, error: GameError | None
    ) -> ClaimRecord:
        """The one place a claim is logged: the moment it is decided."""
        record = ClaimRecord(
            claimant, prize, accepted=error is None, error=error.code if error else None
        )
        self._log.append(record)
        return record

    def log(self) -> list[ClaimRecord]:
        """Every decided claim, in the order it was decided."""
        return list(self._log)

    def board(self) -> dict[Prize, list[str]]:
        """Each prize and the players it was awarded to, empty while it is open. In the order of Prize."""
        return {prize: list(self._awards.get(prize, [])) for prize in Prize}
