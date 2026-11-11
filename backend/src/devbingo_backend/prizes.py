from collections.abc import Callable, Set
from enum import StrEnum

from devbingo_backend.ticket import Ticket


class Prize(StrEnum):
    """The prizes a game can award, in the order the prize board lists them.

    The value is the name the wire uses.
    """

    EARLY_FIVE = "early_five"
    TOP_LINE = "top_line"
    MIDDLE_LINE = "middle_line"
    BOTTOM_LINE = "bottom_line"
    FOUR_CORNERS = "four_corners"
    FULL_HOUSE = "full_house"


EARLY_FIVE_TOPICS = 5

# What each prize needs, as a test of the topics that are on the ticket and both ticked and
# drawn. A prize with no rule here cannot be earned yet.
_RULES: dict[Prize, Callable[[Ticket, Set[str]], bool]] = {
    Prize.EARLY_FIVE: lambda ticket, on_ticket: len(on_ticket) >= EARLY_FIVE_TOPICS,
    Prize.TOP_LINE: lambda ticket, on_ticket: ticket.line(0) <= on_ticket,
    Prize.MIDDLE_LINE: lambda ticket, on_ticket: ticket.line(1) <= on_ticket,
    Prize.BOTTOM_LINE: lambda ticket, on_ticket: ticket.line(2) <= on_ticket,
}


def prizes_earned(ticket: Ticket, ticked_and_drawn: Set[str]) -> set[Prize]:
    """Every prize the ticket satisfies, given the topics ticked and drawn.

    The caller passes only topics that are both ticked and drawn, so this judges the
    pattern alone, not whether a claim is allowed. Topics not on the ticket never count.
    """
    on_ticket = ticked_and_drawn & ticket.topic_names()
    return {prize for prize, rule in _RULES.items() if rule(ticket, on_ticket)}
