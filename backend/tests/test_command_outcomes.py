"""What each command reports, so the adapter only turns outcomes into emits."""

import pytest
from helpers import RealtimeTable, host_message, run

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry, Outcome, PlayerRef


@pytest.fixture
def registry():
    return GameRegistry()


@pytest.fixture
def game(registry):
    return registry.create_game(DEFAULT_POOL)


def test_a_new_player_changes_the_lobby_for_everyone(registry, game):
    registry.join(PlayerRef(game.code, "Ada"))

    joined = registry.join(PlayerRef(game.code, "Grace"))

    assert joined.outcome == Outcome(lobby=("Ada", "Grace"))


def test_a_rejoin_changes_nothing_for_the_others(registry, game):
    ada = PlayerRef(game.code, "Ada")
    registry.join(ada)
    registry.disconnect(ada)

    assert registry.join(ada).outcome == Outcome()


def test_starting_the_game_reports_that_it_started(registry, game):
    assert registry.start(game) == Outcome(started=True)


def test_a_draw_reports_the_topic_drawn(registry, game):
    registry.start(game)

    drawn = registry.draw(game)

    assert drawn.outcome == Outcome(drawn=drawn.draw)
    assert drawn.draw.position == 1


def test_a_failed_announcement_never_costs_the_caller_their_acknowledgement(caplog):
    t = RealtimeTable()
    t.broadcaster.failing = {"lobby_updated", "game_started", "topic_drawn"}

    joined = t.join()
    started = run(t.adapter.start_game("sid-host", host_message(t.game)))
    drawn = run(t.adapter.draw_topic("sid-host", host_message(t.game)))

    assert joined["ok"] is True
    assert started == {"ok": True}
    assert drawn["ok"] is True and drawn["draw"]["position"] == 1
    assert t.registry.host_snapshot(t.game).status == "started"
    assert "could not send" in caplog.text
