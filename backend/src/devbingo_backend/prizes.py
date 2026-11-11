from collections.abc import Set
from enum import StrEnum

from devbingo_backend.ticket import Ticket


class Prize(StrEnum):
    """The prizes a game can award. The value is the name the wire uses."""

    EARLY_FIVE = "early_five"


EARLY_FIVE_TOPICS = 5


def prizes_earned(ticket: Ticket, ticked_and_drawn: Set[str]) -> set[Prize]:
    """The Prize Evaluator: every prize the ticket satisfies, given the topics ticked and drawn.

    The caller passes only topics that are both ticked and drawn, so this judges the
    pattern alone, not whether a claim is allowed. Topics not on the ticket never count.
    """
    on_ticket = ticked_and_drawn & ticket.topic_names()
    earned: set[Prize] = set()
    if len(on_ticket) >= EARLY_FIVE_TOPICS:
        earned.add(Prize.EARLY_FIVE)
    return earned
