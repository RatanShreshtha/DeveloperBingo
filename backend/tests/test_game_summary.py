"""When a game ends, the outcome that ends it carries the game's summary."""

import random

import pytest
from helpers import (
    ManualRegistry,
    ManualScheduler,
    claim_and_settle,
    names_on,
    start_and_draw_everything,
)

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.errors import ErrorCode, GameAlreadyEnded
from devbingo_backend.game import GameRegistry, GameSummary, PlayerRef
from devbingo_backend.prizes import Prize


@pytest.fixture
def setup():
    registry = ManualRegistry(rng=random.Random(5))
    game = registry.create_game(DEFAULT_POOL, pool_name="Default")
    ticket = registry.join(PlayerRef(game.code, "Ada")).snapshot.ticket
    return registry, game, ticket


def summary_of(outcome) -> GameSummary:
    """The summary an outcome carries. The test fails here if the game did not end."""
    assert outcome.summary is not None
    return outcome.summary


def test_nothing_is_summarised_while_the_game_is_running(setup):
    registry, game, _ = setup
    registry.start(game)
    assert registry.draw(game).outcome.summary is None


def test_a_game_ended_by_the_host_is_summarised_with_its_draws_in_order(setup):
    registry, game, _ = setup
    registry.start(game)
    first, second = registry.draw(game).draw, registry.draw(game).draw

    summary = summary_of(registry.end(game))

    assert summary.code == game.code
    assert summary.end_reason == "host"
    assert summary.pool_name == "Default"
    assert summary.draws == (first, second)


def test_a_game_won_by_full_house_is_summarised_with_claims_and_winners(setup):
    registry, game, ticket = setup
    start_and_draw_everything(registry, game)
    ada = PlayerRef(game.code, "Ada")
    for topic in names_on(ticket):
        registry.tick(ada, topic)
    claim_and_settle(registry, ada, Prize.EARLY_FIVE)
    summary = summary_of(claim_and_settle(registry, ada, Prize.FULL_HOUSE))

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
    registry, game, ticket = setup
    start_and_draw_everything(registry, game)
    ada = PlayerRef(game.code, "Ada")
    for topic in names_on(ticket)[:5]:
        registry.tick(ada, topic)
    registry.claim(ada, Prize.EARLY_FIVE)

    summary = summary_of(registry.end(game))

    (claim,) = summary.claims
    assert (claim.accepted, claim.error) == (False, ErrorCode.GAME_ENDED)


def test_a_game_is_summarised_by_the_one_outcome_that_ends_it(setup):
    registry, game, _ = setup
    registry.end(game)
    with pytest.raises(GameAlreadyEnded):
        registry.end(game)


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
