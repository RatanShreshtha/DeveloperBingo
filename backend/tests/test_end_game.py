import random

import pytest
from helpers import claim_and_settle, names_on, start_and_draw_everything

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    ClaimNotValid,
    GameAlreadyEnded,
    GameRegistry,
    NotHost,
    PlayerRef,
)
from devbingo_backend.prizes import Prize
from devbingo_backend.wire import HostLink


@pytest.fixture
def lobby():
    registry = GameRegistry(rng=random.Random(41))
    game = registry.create_game(DEFAULT_POOL)
    ticket = registry.join(PlayerRef(game.code, "Ada")).ticket
    return registry, game, ticket


@pytest.fixture
def started_with_every_topic_drawn(lobby):
    registry, game, ticket = lobby
    start_and_draw_everything(registry, game)
    return registry, game, ticket


def tick_everything(registry, game, ticket):
    for topic in names_on(ticket):
        registry.tick(PlayerRef(game.code, "Ada"), topic)


def test_claiming_full_house_ends_the_game(started_with_every_topic_drawn):
    registry, game, ticket = started_with_every_topic_drawn
    tick_everything(registry, game, ticket)

    outcome = claim_and_settle(registry, PlayerRef(game.code, "Ada"), Prize.FULL_HOUSE)

    assert outcome.ends_game is True
    with pytest.raises(GameAlreadyEnded):
        registry.draw(game)


def test_claiming_any_other_prize_leaves_the_game_running(started_with_every_topic_drawn):
    registry, game, ticket = started_with_every_topic_drawn
    for topic in names_on(ticket)[:5]:
        registry.tick(PlayerRef(game.code, "Ada"), topic)

    outcome = claim_and_settle(registry, PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)

    assert outcome.ends_game is False


def test_a_refused_full_house_claim_does_not_end_the_game(started_with_every_topic_drawn):
    registry, game, ticket = started_with_every_topic_drawn
    for topic in names_on(ticket)[:14]:
        registry.tick(PlayerRef(game.code, "Ada"), topic)

    with pytest.raises(ClaimNotValid):
        registry.claim(PlayerRef(game.code, "Ada"), Prize.FULL_HOUSE)

    claim_and_settle(registry, PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)


def test_the_host_can_end_a_running_game(started_with_every_topic_drawn):
    registry, game, _ = started_with_every_topic_drawn

    registry.end(game)

    with pytest.raises(GameAlreadyEnded):
        registry.draw(game)


def test_the_host_can_end_a_game_still_in_the_lobby(lobby):
    registry, game, _ = lobby

    registry.end(game)

    with pytest.raises(GameAlreadyEnded):
        registry.start(game)


def test_only_the_host_can_end_the_game(started_with_every_topic_drawn):
    registry, game, _ = started_with_every_topic_drawn

    with pytest.raises(NotHost):
        registry.end(HostLink(code=game.code, host_token="not-the-host-token"))

    # The refused attempt ended nothing, so the real host can still end it.
    registry.end(game)


def test_a_game_that_has_ended_cannot_be_ended_again(started_with_every_topic_drawn):
    registry, game, _ = started_with_every_topic_drawn
    registry.end(game)

    with pytest.raises(GameAlreadyEnded):
        registry.end(game)


def test_claims_are_refused_after_the_game_ends(started_with_every_topic_drawn):
    registry, game, ticket = started_with_every_topic_drawn
    for topic in names_on(ticket)[:5]:
        registry.tick(PlayerRef(game.code, "Ada"), topic)
    registry.end(game)

    with pytest.raises(GameAlreadyEnded):
        registry.claim(PlayerRef(game.code, "Ada"), Prize.EARLY_FIVE)

    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == []


def test_a_dropped_player_can_rejoin_after_the_game_ends_to_read_the_result(started_with_every_topic_drawn):
    registry, game, _ = started_with_every_topic_drawn
    ada = PlayerRef(game.code, "Ada")
    registry.disconnect(ada)
    registry.end(game)

    outcome = registry.join(ada)

    assert outcome.is_new_player is False


def test_a_new_player_cannot_join_after_the_game_ends(started_with_every_topic_drawn):
    registry, game, _ = started_with_every_topic_drawn
    registry.end(game)

    with pytest.raises(GameAlreadyEnded):
        registry.join(PlayerRef(game.code, "Late"))


def test_ticks_and_unticks_are_refused_after_the_game_ends(started_with_every_topic_drawn):
    registry, game, ticket = started_with_every_topic_drawn
    ada = PlayerRef(game.code, "Ada")
    topic = names_on(ticket)[0]
    registry.tick(ada, topic)
    registry.end(game)

    with pytest.raises(GameAlreadyEnded):
        registry.untick(ada, topic)
    with pytest.raises(GameAlreadyEnded):
        registry.tick(ada, names_on(ticket)[1])
    assert registry.ticks(ada) == {topic}
