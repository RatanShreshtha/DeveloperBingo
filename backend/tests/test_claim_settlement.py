from dataclasses import dataclass

import pytest
from helpers import board_of, ticket_of

from devbingo_backend.errors import ClaimNotValid, GameAlreadyEnded, PrizeAlreadyAwarded
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimSettlement
from devbingo_backend.wire import ErrorCode

TICKET = ticket_of(
    [
        ["a0", None, "a2", None, "a4", None, "a6", None, "a8"],
        [None, "b1", None, "b3", "b4", "b5", None, "b7", None],
        ["c0", "c1", None, "c3", None, "c5", None, None, "c8"],
    ]
)
FIVE = {"a0", "a2", "a4", "a6", "a8"}
TOO_FEW = {"a0", "a2"}


@dataclass
class Evidence:
    """What each player has ticked and drawn when the window closes."""

    ticked: dict[str, set[str]]

    def __call__(self, name: str):
        return TICKET, self.ticked[name]


def claim(settlement, prize, name, ticked):
    return settlement.claim(prize, name, TICKET, ticked)


def test_a_prize_is_open_until_a_window_closes_with_a_winner():
    settlement = ClaimSettlement()

    assert settlement.board() == board_of()
    assert not settlement.window_open()


def test_the_first_valid_claim_opens_a_window_and_awards_nothing_yet():
    settlement = ClaimSettlement()

    pending = claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)

    assert pending.prize is Prize.EARLY_FIVE
    assert pending.opened_window is True
    assert settlement.window_open()
    assert settlement.board() == board_of()
    assert settlement.log() == []


def test_a_second_valid_claim_in_the_window_wins_together_with_the_first():
    settlement = ClaimSettlement()
    claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)

    pending = claim(settlement, Prize.EARLY_FIVE, "Grace", FIVE)
    settled = settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE, "Grace": FIVE}))

    assert pending.opened_window is False
    assert settled.awarded_to == ("Ada", "Grace")
    assert settled.refused == ()
    assert settlement.board() == board_of(early_five=["Ada", "Grace"])
    assert not settlement.window_open()
    assert [(r.player, r.accepted) for r in settlement.log()] == [("Ada", True), ("Grace", True)]


def test_an_invalid_claim_is_refused_at_once_and_opens_nothing():
    settlement = ClaimSettlement()

    with pytest.raises(ClaimNotValid):
        claim(settlement, Prize.EARLY_FIVE, "Ada", TOO_FEW)

    assert not settlement.window_open()
    assert [(r.player, r.accepted, r.error) for r in settlement.log()] == [
        ("Ada", False, ErrorCode.CLAIM_NOT_VALID)
    ]


def test_claims_are_judged_at_close_so_a_queued_claim_can_fail():
    settlement = ClaimSettlement()
    claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)
    claim(settlement, Prize.EARLY_FIVE, "Grace", TOO_FEW)

    settled = settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE, "Grace": TOO_FEW}))

    assert settled.awarded_to == ("Ada",)
    assert settled.refused == ("Grace",)
    assert [(r.player, r.accepted, r.error) for r in settlement.log()] == [
        ("Ada", True, None),
        ("Grace", False, ErrorCode.CLAIM_NOT_VALID),
    ]


def test_a_claim_is_judged_on_the_evidence_at_close_not_at_arrival():
    settlement = ClaimSettlement()
    claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)
    claim(settlement, Prize.EARLY_FIVE, "Grace", TOO_FEW)

    settled = settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE, "Grace": FIVE}))

    assert settled.awarded_to == ("Ada", "Grace")


def test_a_repeat_claim_by_the_same_player_is_the_same_pending_result():
    settlement = ClaimSettlement()
    first = claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)

    again = claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)
    settled = settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE}))

    assert again.prize == first.prize
    assert again.opened_window is False
    assert settled.awarded_to == ("Ada",)
    assert len(settlement.log()) == 1


def test_a_claim_for_an_awarded_prize_is_refused_at_once():
    settlement = ClaimSettlement()
    claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)
    settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE}))

    with pytest.raises(PrizeAlreadyAwarded):
        claim(settlement, Prize.EARLY_FIVE, "Grace", FIVE)

    assert settlement.board() == board_of(early_five=["Ada"])
    assert settlement.log()[-1].error is ErrorCode.PRIZE_TAKEN


def test_separate_prizes_have_separate_windows_open_together():
    settlement = ClaimSettlement()
    claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)
    claim(settlement, Prize.TOP_LINE, "Grace", FIVE)

    first = settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE}))

    assert first.awarded_to == ("Ada",)
    assert settlement.window_open()
    assert settlement.board() == board_of(early_five=["Ada"])
    assert settlement.close(Prize.TOP_LINE, Evidence({"Grace": FIVE})).awarded_to == ("Grace",)
    assert not settlement.window_open()


def test_a_player_with_a_claim_waiting_is_pending_until_the_window_closes():
    settlement = ClaimSettlement()
    claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)

    assert settlement.has_pending("Ada")
    assert not settlement.has_pending("Grace")

    settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE}))
    assert not settlement.has_pending("Ada")


def test_closing_with_no_window_open_does_nothing():
    assert ClaimSettlement().close(Prize.EARLY_FIVE, Evidence({})) is None


def test_a_window_closed_after_the_game_ended_refuses_every_waiting_claim():
    settlement = ClaimSettlement()
    claim(settlement, Prize.EARLY_FIVE, "Ada", FIVE)

    settled = settlement.close(Prize.EARLY_FIVE, Evidence({"Ada": FIVE}), refusal=GameAlreadyEnded("X"))

    assert settled.awarded_to == ()
    assert settled.refused == ("Ada",)
    assert settlement.board() == board_of()
    assert settlement.log()[0].error is ErrorCode.GAME_ENDED
