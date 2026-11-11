import random

import pytest

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    PlayerRef,
    GameAlreadyStarted,
    GameNotStarted,
    GameRegistry,
    NoTopicsLeft,
    NotHost,
)
from devbingo_backend.wire import HostLink


@pytest.fixture
def started():
    registry = GameRegistry(rng=random.Random(7))
    game = registry.create_game()
    registry.join(PlayerRef(game.code, "Ada"))
    registry.start(game)
    return registry, game


def test_starting_the_game_locks_the_pool(started):
    registry, game = started

    assert registry.is_pool_locked(game.code) is True


def test_the_pool_is_not_locked_before_the_game_starts():
    registry = GameRegistry()
    game = registry.create_game()

    assert registry.is_pool_locked(game.code) is False


def test_the_game_cannot_be_started_twice(started):
    registry, game = started

    with pytest.raises(GameAlreadyStarted):
        registry.start(game)


def test_draws_are_refused_before_the_game_starts():
    registry = GameRegistry()
    game = registry.create_game()

    with pytest.raises(GameNotStarted):
        registry.draw(game)


def test_only_the_host_token_can_draw(started):
    registry, game = started

    with pytest.raises(NotHost):
        registry.draw(HostLink(code=game.code, host_token="not-the-host-token"))


def test_each_draw_is_recorded_in_order_with_its_position(started):
    registry, game = started

    first = registry.draw(game)
    second = registry.draw(game)

    assert [first.position, second.position] == [1, 2]
    assert registry.draw_history(game.code) == (first, second)


def test_a_drawn_topic_carries_its_explanation(started):
    registry, game = started

    draw = registry.draw(game)

    assert draw.topic in DEFAULT_POOL.topics
    assert draw.topic.explanation.strip()


def test_every_topic_is_drawn_once_and_then_none_are_left(started):
    registry, game = started

    draws = [registry.draw(game) for _ in range(90)]

    assert {draw.topic for draw in draws} == set(DEFAULT_POOL.topics)
    assert len({draw.topic for draw in draws}) == 90
    with pytest.raises(NoTopicsLeft):
        registry.draw(game)


def test_the_draw_history_cannot_be_edited_from_outside(started):
    registry, game = started
    registry.draw(game)

    history = registry.draw_history(game.code)

    assert isinstance(history, tuple)
    with pytest.raises(AttributeError):
        history.append(None)  # type: ignore[attr-defined]
