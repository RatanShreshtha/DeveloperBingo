import pytest
from helpers import ticket_of

from devbingo_backend.prizes import Prize, prizes_earned

TICKET = ticket_of(
    [
        ["a0", None, "a2", None, "a4", None, "a6", None, "a8"],
        [None, "b1", None, "b3", "b4", "b5", None, "b7", None],
        ["c0", "c1", None, "c3", None, "c5", None, None, "c8"],
    ]
)

# (what the player has ticked and drawn, the prizes that earns)
CASES = [
    pytest.param(set(), set(), id="nothing ticked earns nothing"),
    pytest.param({"a0", "a2", "a4", "a6"}, set(), id="four topics are not enough for early five"),
    pytest.param({"a0", "a2", "a4", "a6", "a8"}, {Prize.EARLY_FIVE, Prize.TOP_LINE}, id="a complete top line"),
    pytest.param({"b1", "b3", "b4", "b5", "b7"}, {Prize.EARLY_FIVE, Prize.MIDDLE_LINE}, id="a complete middle line"),
    pytest.param({"c0", "c1", "c3", "c5", "c8"}, {Prize.EARLY_FIVE, Prize.BOTTOM_LINE}, id="a complete bottom line"),
    pytest.param({"a0", "a2", "a4", "a6", "b1", "b3", "b4", "b5", "b7"}, {Prize.EARLY_FIVE, Prize.MIDDLE_LINE}, id="four on top and a full middle is only the middle"),
    pytest.param({"a0", "a2", "a4", "a6", "a8", "c0", "c1", "c3", "c5", "c8"}, {Prize.EARLY_FIVE, Prize.TOP_LINE, Prize.BOTTOM_LINE}, id="two complete lines earn both"),
    pytest.param({"a0", "b1", "c3", "c5", "b7"}, {Prize.EARLY_FIVE}, id="five scattered across lines"),
    pytest.param(
        set(TICKET.topic_names()),
        {Prize.EARLY_FIVE, Prize.TOP_LINE, Prize.MIDDLE_LINE, Prize.BOTTOM_LINE, Prize.FULL_HOUSE},
        id="a full ticket earns every prize",
    ),
    pytest.param(
        set(TICKET.topic_names()) - {"c8"},
        {Prize.EARLY_FIVE, Prize.TOP_LINE, Prize.MIDDLE_LINE},
        id="fourteen of fifteen is not a full house",
    ),
    pytest.param(
        {"a0", "a2", "a4", "a6", "zz1", "zz2"},
        set(),
        id="topics that are not on the ticket do not count",
    ),
]


@pytest.mark.parametrize(("ticked_and_drawn", "earned"), CASES)
def test_the_prizes_a_ticket_earns(ticked_and_drawn, earned):
    assert prizes_earned(TICKET, ticked_and_drawn) == earned
