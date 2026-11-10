import random

import pytest

from devbingo_backend.game import (
    MAX_PLAYERS,
    GameAlreadyStarted,
    GameFull,
    GameNotFound,
    GameRegistry,
    NameTaken,
    NotHost,
)


@pytest.fixture
def registry() -> GameRegistry:
    return GameRegistry()


def test_creating_a_game_returns_a_code_and_a_private_host_token(registry):
    created = registry.create_game()

    assert created.code
    assert created.host_token
    assert created.host_token != created.code


def test_joining_returns_the_players_ticket(registry):
    game = registry.create_game()

    ticket = registry.join(game.code, "Ada")

    assert len(ticket.lines) == 3
    assert sum(cell is not None for line in ticket.lines for cell in line) == 15


def test_no_two_tickets_in_a_game_are_identical():
    registry = GameRegistry(rng=random.Random(99))
    game = registry.create_game()

    tickets = [registry.join(game.code, f"player-{i}") for i in range(MAX_PLAYERS)]

    assert len({ticket.lines for ticket in tickets}) == MAX_PLAYERS


def test_players_join_with_a_code_and_a_display_name(registry):
    game = registry.create_game()

    registry.join(game.code, "Ada")
    registry.join(game.code, "Grace")

    assert registry.lobby(game.code, game.host_token) == ["Ada", "Grace"]


def test_a_duplicate_name_is_rejected(registry):
    game = registry.create_game()
    registry.join(game.code, "Ada")

    with pytest.raises(NameTaken):
        registry.join(game.code, "Ada")


def test_the_201st_join_is_rejected(registry):
    game = registry.create_game()
    for i in range(MAX_PLAYERS):
        registry.join(game.code, f"player-{i}")

    with pytest.raises(GameFull):
        registry.join(game.code, "one-too-many")


def test_joins_are_rejected_once_the_game_has_started(registry):
    game = registry.create_game()
    registry.join(game.code, "Ada")
    registry.start(game.code, game.host_token)

    with pytest.raises(GameAlreadyStarted):
        registry.join(game.code, "Late")


def test_joining_an_unknown_game_is_rejected(registry):
    with pytest.raises(GameNotFound):
        registry.join("NOPE00", "Ada")


def test_only_the_host_token_can_read_the_lobby(registry):
    game = registry.create_game()

    with pytest.raises(NotHost):
        registry.lobby(game.code, "not-the-host-token")


def test_only_the_host_token_can_start_the_game(registry):
    game = registry.create_game()

    with pytest.raises(NotHost):
        registry.start(game.code, "not-the-host-token")
