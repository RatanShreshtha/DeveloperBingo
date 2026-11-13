"""When a game ends the registry hands one ended-game summary to its observer."""

import random

import pytest
from helpers import ManualRegistry, ManualScheduler, claim_and_settle, names_on, start_and_draw_everything

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.errors import ErrorCode
from devbingo_backend.game import GameRegistry, PlayerRef
from devbingo_backend.prizes import Prize


@pytest.fixture
def setup():
    summaries = []
    registry = ManualRegistry(rng=random.Random(5), on_ended=summaries.append)
    game = registry.create_game(DEFAULT_POOL, pool_name="Default")
    ticket = registry.join(PlayerRef(game.code, "Ada")).snapshot.ticket
    return registry, game, ticket, summaries


def test_nothing_is_handed_over_while_the_game_is_running(setup):
    registry, game, _, summaries = setup
    registry.start(game)
    registry.draw(game)
    assert summaries == []


def test_a_game_ended_by_the_host_is_summarised_with_its_draws_in_order(setup):
    registry, game, _, summaries = setup
    registry.start(game)
    first, second = registry.draw(game).draw, registry.draw(game).draw

    registry.end(game)

    (summary,) = summaries
    assert summary.code == game.code
    assert summary.end_reason == "host"
    assert summary.pool_name == "Default"
    assert summary.draws == (first, second)


def test_a_game_won_by_full_house_is_summarised_with_claims_and_winners(setup):
    registry, game, ticket, summaries = setup
    start_and_draw_everything(registry, game)
    ada = PlayerRef(game.code, "Ada")
    for topic in names_on(ticket):
        registry.tick(ada, topic)
    claim_and_settle(registry, ada, Prize.EARLY_FIVE)
    claim_and_settle(registry, ada, Prize.FULL_HOUSE)

    (summary,) = summaries
    assert summary.end_reason == "full_house"
    assert len(summary.draws) == 90
    assert [(c.player, c.prize, c.accepted) for c in summary.claims] == [
        ("Ada", Prize.EARLY_FIVE, True),
        ("Ada", Prize.FULL_HOUSE, True),
    ]
    assert summary.prizes[Prize.EARLY_FIVE] == ("Ada",)
    assert summary.prizes[Prize.FULL_HOUSE] == ("Ada",)
    assert summary.prizes[Prize.TOP_LINE] == ()


def test_claims_refused_when_the_host_ends_the_game_are_in_the_summary(setup):
    registry, game, ticket, summaries = setup
    start_and_draw_everything(registry, game)
    ada = PlayerRef(game.code, "Ada")
    for topic in names_on(ticket)[:5]:
        registry.tick(ada, topic)
    registry.claim(ada, Prize.EARLY_FIVE)

    registry.end(game)

    (summary,) = summaries
    (claim,) = summary.claims
    assert (claim.accepted, claim.error) == (False, ErrorCode.GAME_ENDED)


def test_the_summary_is_handed_over_once_even_if_ending_is_tried_again(setup):
    registry, game, _, summaries = setup
    registry.end(game)
    with pytest.raises(Exception):
        registry.end(game)
    assert len(summaries) == 1


def test_a_failing_observer_does_not_stop_the_game_ending(caplog):
    def boom(_summary):
        raise RuntimeError("store down")

    registry = GameRegistry(scheduler=ManualScheduler(), on_ended=boom)
    game = registry.create_game(DEFAULT_POOL)
    with caplog.at_level("ERROR"):
        registry.end(game)

    assert any(r.exc_info for r in caplog.records)
    with pytest.raises(Exception):
        registry.start(game)  # ended


def test_a_code_the_caller_says_is_taken_is_never_handed_to_a_new_game():
    refused: list[str] = []

    def taken(code: str) -> bool:
        if len(refused) < 3:
            refused.append(code)
            return True
        return False

    registry = GameRegistry(scheduler=ManualScheduler(), code_taken=taken)
    link = registry.create_game(DEFAULT_POOL)

    assert len(refused) == 3
    assert link.code not in refused
