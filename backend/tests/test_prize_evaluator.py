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
    pytest.param({"a0", "a2", "a4", "a6", "a8"}, {Prize.EARLY_FIVE}, id="five on one line"),
    pytest.param({"a0", "b1", "c3", "c5", "b7"}, {Prize.EARLY_FIVE}, id="five scattered across lines"),
    pytest.param(set(TICKET.topic_names()), {Prize.EARLY_FIVE}, id="a full ticket still earns early five"),
    pytest.param(
        {"a0", "a2", "a4", "a6", "zz1", "zz2"},
        set(),
        id="topics that are not on the ticket do not count",
    ),
]


@pytest.mark.parametrize(("ticked_and_drawn", "earned"), CASES)
def test_the_prizes_a_ticket_earns(ticked_and_drawn, earned):
    assert prizes_earned(TICKET, ticked_and_drawn) == earned
