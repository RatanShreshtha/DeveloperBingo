import random

import pytest

from helpers import names_on, start_and_draw_everything

from devbingo_backend.game import (
    GameNotStarted,
    GameRegistry,
    NotAPlayer,
    PlayerRef,
    PrizeAlreadyAwarded,
    ClaimNotValid,
)
from devbingo_backend.prizes import Prize


@pytest.fixture
def started_with_every_topic_drawn():
    registry = GameRegistry(rng=random.Random(31))
    game = registry.create_game()
    ada_ticket = registry.join(PlayerRef(game.code, "Ada")).ticket
    grace_ticket = registry.join(PlayerRef(game.code, "Grace")).ticket
    start_and_draw_everything(registry, game)
    return registry, game, ada_ticket, grace_ticket


def tick_n(registry, game, ticket, name, count):
    player = PlayerRef(game.code, name)
    for topic in names_on(ticket)[:count]:
        registry.tick(player, topic)


def test_five_ticked_and_drawn_topics_award_early_five(started_with_every_topic_drawn):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick_n(registry, game, ada_ticket, "Ada", 5)

    outcome = registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)

    assert outcome.prize is Prize.EARLY_FIVE
    assert outcome.winner == "Ada"
    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == "Ada"


def test_fewer_than_five_ticks_is_not_a_valid_early_five(started_with_every_topic_drawn):
    registry, game, ada_ticket, _ = started_with_every_topic_drawn
    tick_n(registry, game, ada_ticket, "Ada", 4)
    board_before = registry.prize_board(game.code)
    ticks_before = registry.ticks(PlayerRef(game.code, "Ada"))

    with pytest.raises(ClaimNotValid):
        registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)

    assert registry.prize_board(game.code) == board_before
    assert registry.ticks(PlayerRef(game.code, "Ada")) == ticks_before


def test_the_prize_is_awarded_once_per_game(started_with_every_topic_drawn):
    registry, game, ada_ticket, grace_ticket = started_with_every_topic_drawn
    tick_n(registry, game, ada_ticket, "Ada", 5)
    tick_n(registry, game, grace_ticket, "Grace", 5)
    registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)

    with pytest.raises(PrizeAlreadyAwarded):
        registry.claim(PlayerRef(game.code, "Grace"), Prize.EARLY_FIVE)

    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == "Ada"


def test_a_prize_remains_open_until_someone_claims_it(started_with_every_topic_drawn):
    registry, game, _, _ = started_with_every_topic_drawn

    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] is None


def test_claims_are_refused_before_the_game_starts():
    registry = GameRegistry(rng=random.Random(31))
    game = registry.create_game()
    registry.join(PlayerRef(game.code, "Ada"))

    with pytest.raises(GameNotStarted):
        registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)


def test_only_players_in_the_game_can_claim(started_with_every_topic_drawn):
    registry, game, _, _ = started_with_every_topic_drawn

    with pytest.raises(NotAPlayer):
        registry.claim(PlayerRef(game.code, "Nobody"), Prize.EARLY_FIVE)
