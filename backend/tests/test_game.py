import random

import pytest

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    PlayerRef,
    MAX_PLAYERS,
    GameAlreadyStarted,
    GameFull,
    GameNotFound,
    GameRegistry,
    NameTaken,
    NotHost,
)
from devbingo_backend.wire import HostLink
from helpers import ManualScheduler


@pytest.fixture
def registry() -> GameRegistry:
    return GameRegistry(scheduler=ManualScheduler())


def test_creating_a_game_returns_a_code_and_a_private_host_token(registry):
    created = registry.create_game(DEFAULT_POOL)

    assert created.code
    assert created.host_token
    assert created.host_token != created.code


def test_joining_returns_the_players_ticket(registry):
    game = registry.create_game(DEFAULT_POOL)

    ticket = registry.join(PlayerRef(game.code, "Ada")).ticket

    assert len(ticket.lines) == 3
    assert sum(cell is not None for line in ticket.lines for cell in line) == 15


def test_a_first_join_is_reported_as_a_new_player(registry):
    game = registry.create_game(DEFAULT_POOL)

    outcome = registry.join(PlayerRef(game.code, "Ada"))

    assert outcome.is_new_player is True


def test_no_two_tickets_in_a_game_are_identical():
    registry = GameRegistry(scheduler=ManualScheduler(), rng=random.Random(99))
    game = registry.create_game(DEFAULT_POOL)

    tickets = [registry.join(PlayerRef(game.code, f"player-{i}")).ticket for i in range(MAX_PLAYERS)]

    assert len({ticket.lines for ticket in tickets}) == MAX_PLAYERS


def test_players_join_with_a_code_and_a_display_name(registry):
    game = registry.create_game(DEFAULT_POOL)

    registry.join(PlayerRef(game.code, "Ada"))
    registry.join(PlayerRef(game.code, "Grace"))

    assert registry.lobby(game) == ["Ada", "Grace"]


def test_a_duplicate_name_is_rejected(registry):
    game = registry.create_game(DEFAULT_POOL)
    registry.join(PlayerRef(game.code, "Ada"))

    with pytest.raises(NameTaken):
        registry.join(PlayerRef(game.code, "Ada"))


def test_the_201st_join_is_rejected(registry):
    game = registry.create_game(DEFAULT_POOL)
    for i in range(MAX_PLAYERS):
        registry.join(PlayerRef(game.code, f"player-{i}"))

    with pytest.raises(GameFull):
        registry.join(PlayerRef(game.code, "one-too-many"))


def test_joins_are_rejected_once_the_game_has_started(registry):
    game = registry.create_game(DEFAULT_POOL)
    registry.join(PlayerRef(game.code, "Ada"))
    registry.start(game)

    with pytest.raises(GameAlreadyStarted):
        registry.join(PlayerRef(game.code, "Late"))


def test_joining_an_unknown_game_is_rejected(registry):
    with pytest.raises(GameNotFound):
        registry.join(PlayerRef("NOPE00", "Ada"))


def test_only_the_host_token_can_read_the_lobby(registry):
    game = registry.create_game(DEFAULT_POOL)

    with pytest.raises(NotHost):
        registry.lobby(HostLink(code=game.code, host_token="not-the-host-token"))


def test_only_the_host_token_can_start_the_game(registry):
    game = registry.create_game(DEFAULT_POOL)

    with pytest.raises(NotHost):
        registry.start(HostLink(code=game.code, host_token="not-the-host-token"))
