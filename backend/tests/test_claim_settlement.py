"""Edge cases of the judging inside a settlement window that the game registry's interface does not
reach easily. Everything else about windows is tested through the registry."""

from dataclasses import dataclass

from helpers import ticket_of

from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimSettlement

TICKET = ticket_of(
    [
        ["a0", None, "a2", None, "a4", None, "a6", None, "a8"],
        [None, "b1", None, "b3", "b4", "b5", None, "b7", None],
        ["c0", "c1", None, "c3", None, "c5", None, None, "c8"],
    ]
)
FIVE = {"a0", "a2", "a4", "a6", "a8"}


@dataclass
class Evidence:
    """What each player has ticked and drawn when the window closes."""

    ticked: dict[str, set[str]]

    def __call__(self, name: str):
        return TICKET, self.ticked[name]


def claim(settlement, prize, name, ticked):
    return settlement.claim(prize, name, TICKET, ticked)


def test_a_repeat_claim_by_the_same_player_is_the_same_pending_result():
    settlement = ClaimSettlement()
    first = claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)

    again = claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)
    settled = settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE}))

    assert again.prize == first.prize
    assert again.opened_window is False
    assert settled.awarded_to == ("Ada",)
    assert len(settlement.log()) == 1


def test_a_player_with_a_claim_waiting_is_pending_until_the_window_closes():
    settlement = ClaimSettlement()
    claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)

    assert settlement.has_pending("Ada")
    assert not settlement.has_pending("Grace")

    settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE}))
    assert not settlement.has_pending("Ada")
