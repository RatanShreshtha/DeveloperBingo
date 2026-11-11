from collections.abc import Set
from dataclasses import dataclass, field

from devbingo_backend.errors import ClaimNotValid, PrizeAlreadyAwarded
from devbingo_backend.prizes import Prize, prizes_earned
from devbingo_backend.ticket import Ticket


@dataclass(frozen=True)
class Awarded:
    """A valid claim: the prize, and the display names of every player it is now awarded to."""

    prize: Prize
    awarded_to: tuple[str, ...]


@dataclass
class ClaimSettlement:
    """Judges claims for one game and holds who each prize was awarded to.

    A prize can hold several players, so the settlement window (ticket 12) can award
    simultaneous claims together. Until then each prize is awarded to one player.
    """

    _awards: dict[Prize, list[str]] = field(default_factory=dict)

    def claim(self, prize: Prize, claimant: str, ticket: Ticket, ticked_and_drawn: Set[str]) -> Awarded:
        """Award the prize to the claimant if their ticket earns it. A refused claim changes nothing."""
        if prize in self._awards:
            raise PrizeAlreadyAwarded(prize)
        if prize not in prizes_earned(ticket, ticked_and_drawn):
            raise ClaimNotValid(prize)
        self._awards[prize] = [claimant]
        return Awarded(prize, tuple(self._awards[prize]))

    def board(self) -> dict[Prize, list[str]]:
        """Each prize and the players it was awarded to, empty while it is open. In the order of Prize."""
        return {prize: list(self._awards.get(prize, [])) for prize in Prize}
