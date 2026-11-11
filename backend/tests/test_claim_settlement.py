import pytest
from helpers import board_of, ticket_of

from devbingo_backend.game import ClaimNotValid, PrizeAlreadyAwarded
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


def test_a_prize_is_open_until_a_valid_claim_awards_it():
    settlement = ClaimSettlement()

    assert settlement.board() == board_of()


def test_a_valid_claim_awards_the_prize_to_the_claimant():
    settlement = ClaimSettlement()

    outcome = settlement.claim(Prize.EARLY_FIVE, "Ada", TICKET, FIVE)

    assert outcome.prize is Prize.EARLY_FIVE
    assert outcome.awarded_to == ("Ada",)
    assert settlement.board() == board_of(early_five=["Ada"])


def test_a_claim_the_ticket_does_not_support_is_refused_and_awards_nothing():
    settlement = ClaimSettlement()

    with pytest.raises(ClaimNotValid):
        settlement.claim(Prize.EARLY_FIVE, "Ada", TICKET, {"a0", "a2"})

    assert settlement.board() == board_of()


def test_an_awarded_prize_is_refused_to_a_second_claimant_and_keeps_its_winner():
    settlement = ClaimSettlement()
    settlement.claim(Prize.EARLY_FIVE, "Ada", TICKET, FIVE)

    with pytest.raises(PrizeAlreadyAwarded):
        settlement.claim(Prize.EARLY_FIVE, "Grace", TICKET, FIVE)

    assert settlement.board() == board_of(early_five=["Ada"])
