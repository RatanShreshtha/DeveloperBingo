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
Rule = Callable[[Ticket, Set[str]], bool]


def _line_rule(index: int) -> Rule:
    return lambda ticket, on_ticket: ticket.line(index) <= on_ticket


_RULES: dict[Prize, Rule] = {
    Prize.EARLY_FIVE: lambda ticket, on_ticket: len(on_ticket) >= EARLY_FIVE_TOPICS,
    Prize.TOP_LINE: _line_rule(0),
    Prize.MIDDLE_LINE: _line_rule(1),
    Prize.BOTTOM_LINE: _line_rule(2),
    Prize.FOUR_CORNERS: lambda ticket, on_ticket: ticket.four_corners() <= on_ticket,
    Prize.FULL_HOUSE: lambda ticket, on_ticket: on_ticket == ticket.topic_names(),
}


def prizes_earned(ticket: Ticket, ticked_and_drawn: Set[str]) -> set[Prize]:
    """Every prize the ticket satisfies, given the topics ticked and drawn.

    The caller passes only topics that are both ticked and drawn, so this judges the
    pattern alone, not whether a claim is allowed. Topics not on the ticket never count.
    """
    on_ticket = ticked_and_drawn & ticket.topic_names()
    return {prize for prize, rule in _RULES.items() if rule(ticket, on_ticket)}
