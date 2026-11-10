import random

import pytest

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    GameRegistry,
    NotAPlayer,
    PlayerRef,
    TopicNotDrawn,
    TopicNotOnTicket,
)


def names_on(ticket) -> set[str]:
    """The topic names on a ticket, read straight from its lines.

    Deliberately independent of the engine's own helper, so the tests check
    the engine against the ticket's contents rather than against itself.
    """
    return {cell.name for line in ticket.lines for cell in line if cell is not None}


@pytest.fixture
def game_with_ada():
    registry = GameRegistry(rng=random.Random(11))
    game = registry.create_game()
    ticket = registry.join(PlayerRef(game.code, "Ada"))
    registry.start(game.host_link)
    return registry, game, ticket


def draw_everything(registry, game):
    for _ in range(len(DEFAULT_POOL.topics)):
        registry.draw(game.host_link)


def test_a_drawn_topic_on_the_players_ticket_can_be_ticked(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    draw_everything(registry, game)
    topic = sorted(names_on(ticket))[0]

    registry.tick(ada, topic)

    assert topic in registry.ticks(ada)


def test_an_undrawn_topic_cannot_be_ticked_and_the_ticks_are_unchanged(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    undrawn_on_ticket = sorted(names_on(ticket))[0]
    before = registry.ticks(ada)

    with pytest.raises(TopicNotDrawn):
        registry.tick(ada, undrawn_on_ticket)

    assert registry.ticks(ada) == before


def test_a_topic_not_on_the_players_ticket_cannot_be_ticked(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    draw_everything(registry, game)
    off_ticket = next(topic.name for topic in DEFAULT_POOL.topics if topic.name not in names_on(ticket))

    with pytest.raises(TopicNotOnTicket):
        registry.tick(ada, off_ticket)


def test_a_ticked_topic_can_be_unticked(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    draw_everything(registry, game)
    topic = sorted(names_on(ticket))[0]
    registry.tick(ada, topic)

    registry.untick(ada, topic)

    assert topic not in registry.ticks(ada)


def test_an_untick_of_a_topic_not_on_the_ticket_is_refused(game_with_ada):
    registry, game, ticket = game_with_ada
    ada = PlayerRef(game.code, "Ada")
    draw_everything(registry, game)
    registry.tick(ada, sorted(names_on(ticket))[0])
    before = registry.ticks(ada)
    off_ticket = next(topic.name for topic in DEFAULT_POOL.topics if topic.name not in names_on(ticket))

    with pytest.raises(TopicNotOnTicket):
        registry.untick(ada, off_ticket)

    assert registry.ticks(ada) == before


def test_only_players_in_the_game_can_tick(game_with_ada):
    registry, game, ticket = game_with_ada
    draw_everything(registry, game)

    with pytest.raises(NotAPlayer):
        registry.tick(PlayerRef(game.code, "Grace"), sorted(names_on(ticket))[0])


def test_each_players_ticks_belong_to_that_player():
    registry = GameRegistry(rng=random.Random(11))
    game = registry.create_game()
    ada_ticket = registry.join(PlayerRef(game.code, "Ada"))
    registry.join(PlayerRef(game.code, "Grace"))
    registry.start(game.host_link)
    draw_everything(registry, game)
    topic = sorted(names_on(ada_ticket))[0]

    registry.tick(PlayerRef(game.code, "Ada"), topic)

    assert topic in registry.ticks(PlayerRef(game.code, "Ada"))
    assert registry.ticks(PlayerRef(game.code, "Grace")) == frozenset()
