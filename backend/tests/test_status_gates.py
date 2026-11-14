"""Which game status refuses each command, and with which error. One table of status gates, so a
change to the rules shows up in one place."""

import random

import pytest
from helpers import ManualRegistry

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.errors import GameAlreadyEnded, GameAlreadyStarted, GameNotStarted
from devbingo_backend.game import PlayerRef
from devbingo_backend.prizes import Prize


def game_in(status: str):
    """A game in the given status, with Ada in the lobby."""
    registry = ManualRegistry(rng=random.Random(5))
    game = registry.create_game(DEFAULT_POOL)
    ada = PlayerRef(game.code, "Ada")
    registry.join(ada)
    if status != "lobby":
        registry.start(game)
    if status == "ended":
        registry.end(game)
    return registry, game, ada


@pytest.mark.parametrize(
    ("status", "error"),
    [("lobby", None), ("started", GameAlreadyStarted), ("ended", GameAlreadyEnded)],
)
def test_start_needs_the_lobby(status, error):
    registry, game, _ = game_in(status)
    if error is None:
        registry.start(game)
    else:
        with pytest.raises(error):
            registry.start(game)


@pytest.mark.parametrize(
    ("status", "error"),
    [("lobby", None), ("started", GameAlreadyStarted), ("ended", GameAlreadyEnded)],
)
def test_a_new_player_can_join_only_in_the_lobby(status, error):
    registry, game, _ = game_in(status)
    linus = PlayerRef(game.code, "Linus")
    if error is None:
        registry.join(linus)
    else:
        with pytest.raises(error):
            registry.join(linus)


@pytest.mark.parametrize(
    ("status", "error"),
    [("lobby", GameNotStarted), ("started", None), ("ended", GameAlreadyEnded)],
)
def test_a_draw_needs_a_started_game(status, error):
    registry, game, _ = game_in(status)
    if error is None:
        registry.draw(game)
    else:
        with pytest.raises(error):
            registry.draw(game)


@pytest.mark.parametrize("status", ["lobby", "started", "ended"])
def test_the_host_can_end_the_game_from_any_status_once(status):
    registry, game, _ = game_in(status)
    if status == "ended":
        with pytest.raises(GameAlreadyEnded):
            registry.end(game)
    else:
        registry.end(game)
        with pytest.raises(GameAlreadyEnded):
            registry.end(game)


@pytest.mark.parametrize("command", ["tick", "untick"])
def test_ticks_are_refused_once_the_game_has_ended(command):
    registry, game, ada = game_in("ended")
    change = registry.tick if command == "tick" else registry.untick
    with pytest.raises(GameAlreadyEnded):
        change(ada, "Matrix")


@pytest.mark.parametrize(
    ("status", "error"),
    [("lobby", GameNotStarted), ("ended", GameAlreadyEnded)],
)
def test_a_claim_is_logged_as_refused_outside_a_started_game(status, error):
    registry, _, ada = game_in(status)
    result = registry.claim(ada, Prize.EARLY_FIVE)
    assert type(result.refusal) is error
