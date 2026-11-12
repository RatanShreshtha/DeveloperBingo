import random

import pytest
from helpers import ManualScheduler, draw_everything, names_on

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    GameRegistry,
    NotAPlayer,
    PlayerRef,
    TopicNotDrawn,
    TopicNotOnTicket,
)


@pytest.fixture
def game_with_ada():
    registry = GameRegistry(scheduler=ManualScheduler(), rng=random.Random(11))
    game = registry.create_game(DEFAULT_POOL)
    ticket = registry.join(PlayerRef(game.code, "Ada")).ticket
    registry.start(game)
    return registry, game, ticket


def test_a_drawn_topic_on_the_players_ticket_can_be_ticked(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    draw_everything(registry, game)
    topic = names_on(ticket)[0]

    registry.tick(ada, topic)

    assert topic in registry.ticks(ada)


def test_an_undrawn_topic_cannot_be_ticked_and_the_ticks_are_unchanged(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    undrawn_on_ticket = names_on(ticket)[0]
    before = registry.ticks(ada)

    with pytest.raises(TopicNotDrawn):
        registry.tick(ada, undrawn_on_ticket)

    assert registry.ticks(ada) == before


def test_a_topic_not_on_the_players_ticket_cannot_be_ticked(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    draw_everything(registry, game)
    off_ticket = next(topic.name for topic in DEFAULT_POOL.topics if topic.name not in set(names_on(ticket)))

    with pytest.raises(TopicNotOnTicket):
        registry.tick(ada, off_ticket)


def test_a_ticked_topic_can_be_unticked(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    draw_everything(registry, game)
    topic = names_on(ticket)[0]
    registry.tick(ada, topic)

    registry.untick(ada, topic)

    assert topic not in registry.ticks(ada)


def test_an_untick_of_a_topic_not_on_the_ticket_is_refused(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    draw_everything(registry, game)
    registry.tick(ada, names_on(ticket)[0])
    before = registry.ticks(ada)
    off_ticket = next(topic.name for topic in DEFAULT_POOL.topics if topic.name not in set(names_on(ticket)))

    with pytest.raises(TopicNotOnTicket):
        registry.untick(ada, off_ticket)

    assert registry.ticks(ada) == before


def test_only_players_in_the_game_can_tick(game_with_ada):
    registry, game, ticket = game_with_ada
    draw_everything(registry, game)

    with pytest.raises(NotAPlayer):
        registry.tick(PlayerRef(game.code, "Grace"), names_on(ticket)[0])


def test_each_players_ticks_belong_to_that_player():
    registry = GameRegistry(scheduler=ManualScheduler(), rng=random.Random(11))
    game = registry.create_game(DEFAULT_POOL)
    ada_ticket = registry.join(PlayerRef(game.code, "Ada")).ticket
    registry.join(PlayerRef(game.code, "Grace"))
    registry.start(game)
    draw_everything(registry, game)
    topic = names_on(ada_ticket)[0]

    registry.tick(PlayerRef(game.code, "Ada"), topic)

    assert topic in registry.ticks(PlayerRef(game.code, "Ada"))
    assert registry.ticks(PlayerRef(game.code, "Grace")) == frozenset()
