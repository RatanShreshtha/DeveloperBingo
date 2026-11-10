import random

import pytest

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    GameRegistry,
    NotAPlayer,
    TopicNotDrawn,
    TopicNotOnTicket,
)


def names_on(ticket) -> set[str]:
    return {cell.name for line in ticket.lines for cell in line if cell is not None}


@pytest.fixture
def game_with_ada():
    registry = GameRegistry(rng=random.Random(11))
    game = registry.create_game()
    ticket = registry.join(game.code, "Ada")
    registry.start(game.host_link)
    return registry, game, ticket


def draw_everything(registry, game):
    for _ in range(len(DEFAULT_POOL.topics)):
        registry.draw(game.host_link)


def test_a_drawn_topic_on_the_players_ticket_can_be_ticked(game_with_ada):
    registry, game, ticket = game_with_ada
    draw_everything(registry, game)
    topic = sorted(names_on(ticket))[0]

    ticked = registry.tick(game.code, "Ada", topic)

    assert topic in ticked
    assert registry.ticks(game.code, "Ada") == ticked


def test_an_undrawn_topic_cannot_be_ticked_and_the_ticks_are_unchanged(game_with_ada):
    registry, game, ticket = game_with_ada
    undrawn_on_ticket = sorted(names_on(ticket))[0]
    before = registry.ticks(game.code, "Ada")

    with pytest.raises(TopicNotDrawn):
        registry.tick(game.code, "Ada", undrawn_on_ticket)

    assert registry.ticks(game.code, "Ada") == before


def test_a_topic_not_on_the_players_ticket_cannot_be_ticked(game_with_ada):
    registry, game, ticket = game_with_ada
    draw_everything(registry, game)
    off_ticket = next(topic.name for topic in DEFAULT_POOL.topics if topic.name not in names_on(ticket))

    with pytest.raises(TopicNotOnTicket):
        registry.tick(game.code, "Ada", off_ticket)


def test_a_ticked_topic_can_be_unticked(game_with_ada):
    registry, game, ticket = game_with_ada
    draw_everything(registry, game)
    topic = sorted(names_on(ticket))[0]
    registry.tick(game.code, "Ada", topic)

    registry.untick(game.code, "Ada", topic)

    assert topic not in registry.ticks(game.code, "Ada")


def test_only_players_in_the_game_can_tick(game_with_ada):
    registry, game, ticket = game_with_ada
    draw_everything(registry, game)

    with pytest.raises(NotAPlayer):
        registry.tick(game.code, "Grace", sorted(names_on(ticket))[0])


def test_each_players_ticks_belong_to_that_player():
    registry = GameRegistry(rng=random.Random(11))
    game = registry.create_game()
    ada_ticket = registry.join(game.code, "Ada")
    registry.join(game.code, "Grace")
    registry.start(game.host_link)
    draw_everything(registry, game)
    topic = sorted(names_on(ada_ticket))[0]

    registry.tick(game.code, "Ada", topic)

    assert topic in registry.ticks(game.code, "Ada")
    assert registry.ticks(game.code, "Grace") == frozenset()
