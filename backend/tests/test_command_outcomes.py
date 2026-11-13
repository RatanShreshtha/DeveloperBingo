"""What each command reports, so the adapter only turns outcomes into emits."""

import asyncio

import pytest
from helpers import ManualScheduler

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry, Outcome, PlayerRef
from devbingo_backend.realtime import RealtimeAdapter


@pytest.fixture
def registry():
    return GameRegistry(scheduler=ManualScheduler())


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


class BrokenBroadcaster:
    """Takes sockets into rooms, but every message it is asked to send fails."""

    async def enter_room(self, sid: str, room: str) -> None:
        pass

    async def leave_room(self, sid: str, room: str) -> None:
        pass

    async def emit(self, event, data, room=None, to=None) -> None:
        raise RuntimeError(f"cannot emit {event}")


def test_a_failed_announcement_never_costs_the_caller_their_acknowledgement(registry, game, caplog):
    adapter = RealtimeAdapter(registry, BrokenBroadcaster())
    host = {"code": game.code, "host_token": game.host_token}

    async def commands():
        joined = await adapter.join_game("sid-1", {"code": game.code, "name": "Ada"})
        started = await adapter.start_game("sid-host", host)
        drawn = await adapter.draw_topic("sid-host", host)
        return joined, started, drawn

    joined, started, drawn = asyncio.run(commands())

    assert joined["ok"] is True
    assert started == {"ok": True}
    assert drawn["ok"] is True and drawn["draw"]["position"] == 1
    assert registry.host_snapshot(game).status == "started"
    assert "cannot emit" in caplog.text or "could not send" in caplog.text
