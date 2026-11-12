import random

import pytest
from helpers import names_on, start_and_draw_everything

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
    game = registry.create_game(DEFAULT_POOL)
    ada_ticket = registry.join(PlayerRef(game.code, "Ada")).ticket
    return registry, game, ada_ticket


def test_a_name_is_refused_while_its_player_is_connected(lobby):
    registry, game, _ = lobby

    with pytest.raises(NameTaken):
        registry.join(PlayerRef(game.code, "Ada"))



def test_a_rejoin_is_reported_as_not_a_new_player(lobby):
    registry, game, _ = lobby
    ada = PlayerRef(game.code, "Ada")
    registry.disconnect(ada)

    outcome = registry.join(ada)

    assert outcome.is_new_player is False


def test_rejoining_restores_the_players_ticks(lobby):
    registry, game, ada_ticket = lobby
    ada = PlayerRef(game.code, "Ada")
    start_and_draw_everything(registry, game)
    topic = names_on(ada_ticket)[0]
    registry.tick(ada, topic)
    registry.disconnect(ada)

    registry.join(PlayerRef(game.code, "Ada"))

    assert topic in registry.ticks(ada)


def test_a_rejoin_after_the_game_starts_is_still_a_restore(lobby):
    registry, game, ada_ticket = lobby
    registry.start(game)
    registry.disconnect(PlayerRef(game.code, "Ada"))

    rejoined = registry.join(PlayerRef(game.code, "Ada")).ticket

    assert rejoined.lines == ada_ticket.lines


def test_a_new_name_after_the_game_starts_is_refused(lobby):
    registry, game, _ = lobby
    registry.start(game)

    with pytest.raises(GameAlreadyStarted):
        registry.join(PlayerRef(game.code, "Grace"))


def test_a_name_that_belongs_to_no_one_is_a_new_join_not_a_restore(lobby):
    registry, game, _ = lobby

    grace_ticket = registry.join(PlayerRef(game.code, "Grace")).ticket

    assert registry.players(game.code) == ["Ada", "Grace"]
    assert registry.ticks(PlayerRef(game.code, "Grace")) == frozenset()
    assert grace_ticket.lines != lobby[2].lines


def test_disconnecting_a_player_who_is_not_in_the_game_is_refused(lobby):
    registry, game, _ = lobby

    with pytest.raises(NotAPlayer):
        registry.disconnect(PlayerRef(game.code, "Nobody"))


def test_names_match_without_regard_to_case(lobby):
    registry, game, ada_ticket = lobby

    with pytest.raises(NameTaken):
        registry.join(PlayerRef(game.code, "ada"))

    registry.disconnect(PlayerRef(game.code, "Ada"))
    rejoined = registry.join(PlayerRef(game.code, "ADA")).ticket

    assert rejoined.lines == ada_ticket.lines
    assert registry.players(game.code) == ["Ada"]
