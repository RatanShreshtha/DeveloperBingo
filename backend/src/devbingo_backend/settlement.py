from collections.abc import Set
from dataclasses import dataclass, field

from devbingo_backend.errors import ClaimNotValid, GameError, PrizeAlreadyAwarded
from devbingo_backend.prizes import Prize, prizes_earned
from devbingo_backend.ticket import Ticket
from devbingo_backend.wire import ErrorCode


@dataclass(frozen=True)
class Awarded:
    """A valid claim: the prize, and the display names of every player it is now awarded to."""

    prize: Prize
    awarded_to: tuple[str, ...]
    # True when this prize is the one that ends the game.
    ends_game: bool = False


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

    A prize can hold several players, so the settlement window (ticket 12) can award
    simultaneous claims together. Until then each prize is awarded to one player.
    """

    _awards: dict[Prize, list[str]] = field(default_factory=dict)
    _log: list[ClaimRecord] = field(default_factory=list)

    def claim(
        self,
        prize: Prize,
        claimant: str,
        ticket: Ticket,
        ticked_and_drawn: Set[str],
        refusal: GameError | None = None,
    ) -> Awarded:
        """Award the prize to the claimant if their ticket earns it. A refused claim changes nothing.

        `refusal` is a rule the game already broke (it has ended, or not started): the claim is
        refused for it. Every claim decided here, accepted or refused, is logged, in this one place.
        """
        try:
            awarded = self._judge(prize, claimant, ticket, ticked_and_drawn, refusal)
        except GameError as err:
            self._log.append(ClaimRecord(claimant, prize, accepted=False, error=err.code))
            raise
        self._log.append(ClaimRecord(claimant, prize, accepted=True))
        return awarded

    def _judge(
        self,
        prize: Prize,
        claimant: str,
        ticket: Ticket,
        ticked_and_drawn: Set[str],
        refusal: GameError | None,
    ) -> Awarded:
        if refusal is not None:
            raise refusal
        if prize in self._awards:
            raise PrizeAlreadyAwarded(prize)
        if prize not in prizes_earned(ticket, ticked_and_drawn):
            raise ClaimNotValid(prize)
        self._awards[prize] = [claimant]
        return Awarded(prize, tuple(self._awards[prize]))

    def log(self) -> list[ClaimRecord]:
        """Every decided claim, in the order it was decided."""
        return list(self._log)

    def board(self) -> dict[Prize, list[str]]:
        """Each prize and the players it was awarded to, empty while it is open. In the order of Prize."""
        return {prize: list(self._awards.get(prize, [])) for prize in Prize}
