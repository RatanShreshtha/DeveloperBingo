import random

import pytest

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    GameAlreadyStarted,
    GameRegistry,
    NameTaken,
    NotAPlayer,
    PlayerRef,
)


@pytest.fixture
def lobby():
    registry = GameRegistry(rng=random.Random(21))
    game = registry.create_game()
    ada_ticket = registry.join(game.code, "Ada")
    return registry, game, ada_ticket


def test_a_name_is_refused_while_its_player_is_connected(lobby):
    registry, game, _ = lobby

    with pytest.raises(NameTaken):
        registry.join(game.code, "Ada")


def test_rejoining_after_a_drop_restores_the_same_ticket(lobby):
    registry, game, ada_ticket = lobby
    registry.disconnect(PlayerRef(game.code, "Ada"))

    rejoined = registry.join(game.code, "Ada")

    assert rejoined.lines == ada_ticket.lines


def test_rejoining_restores_the_players_ticks(lobby):
    registry, game, ada_ticket = lobby
    ada = PlayerRef(game.code, "Ada")
    registry.start(game.host_link)
    for _ in range(len(DEFAULT_POOL.topics)):
        registry.draw(game.host_link)
    topic = next(cell.name for line in ada_ticket.lines for cell in line if cell)
    registry.tick(ada, topic)
    registry.disconnect(ada)

    registry.join(game.code, "Ada")

    assert topic in registry.ticks(ada)


def test_a_rejoin_after_the_game_starts_is_still_a_restore(lobby):
    registry, game, ada_ticket = lobby
    registry.start(game.host_link)
    registry.disconnect(PlayerRef(game.code, "Ada"))

    rejoined = registry.join(game.code, "Ada")

    assert rejoined.lines == ada_ticket.lines


def test_a_new_name_after_the_game_starts_is_refused(lobby):
    registry, game, _ = lobby
    registry.start(game.host_link)

    with pytest.raises(GameAlreadyStarted):
        registry.join(game.code, "Grace")


def test_a_name_that_belongs_to_no_one_is_a_new_join_not_a_restore(lobby):
    registry, game, _ = lobby

    grace_ticket = registry.join(game.code, "Grace")

    assert registry.players(game.code) == ["Ada", "Grace"]
    assert registry.ticks(PlayerRef(game.code, "Grace")) == frozenset()
    assert grace_ticket.lines != lobby[2].lines


def test_disconnecting_a_player_who_is_not_in_the_game_is_refused(lobby):
    registry, game, _ = lobby

    with pytest.raises(NotAPlayer):
        registry.disconnect(PlayerRef(game.code, "Nobody"))
