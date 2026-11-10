import asyncio
import random

from devbingo_backend.game import GameRegistry
from devbingo_backend.realtime import RealtimeAdapter


class RecordingBroadcaster:
    """Stands in for the Socket.IO server and records what it was asked to do."""

    def __init__(self) -> None:
        self.entered: list[tuple[str, str]] = []
        self.emitted: list[tuple[str, str, object]] = []

    async def enter_room(self, sid: str, room: str) -> None:
        self.entered.append((sid, room))

    async def emit(self, event: str, data: object, room: str | None = None,
                   to: str | None = None) -> None:
        self.emitted.append((event, room or to or "", data))


def run(coro):
    return asyncio.run(coro)


def test_a_join_becomes_an_engine_command_and_a_room_broadcast():
    registry = GameRegistry()
    game = registry.create_game()
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.join_game("sid-1", {"code": game.code, "name": "Ada"}))

    assert ack["ok"] is True
    assert len(ack["ticket"]) == 3
    assert all(len(line) == 9 for line in ack["ticket"])
    assert registry.lobby(game.host_link) == ["Ada"]
    assert broadcaster.entered == [("sid-1", game.code)]
    assert broadcaster.emitted == [
        ("lobby_updated", game.code, {"players": ["Ada"]}),
    ]


def test_a_rejected_join_is_acknowledged_to_the_sender_only():
    registry = GameRegistry()
    game = registry.create_game()
    registry.join(game.code, "Ada")
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.join_game("sid-2", {"code": game.code, "name": "Ada"}))

    assert ack == {"ok": False, "error": "name_taken"}
    assert broadcaster.emitted == []
    assert broadcaster.entered == []


def test_the_host_can_watch_the_lobby_with_the_host_token():
    registry = GameRegistry()
    game = registry.create_game()
    registry.join(game.code, "Ada")
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.watch_lobby(
        "sid-host", {"code": game.code, "host_token": game.host_token}
    ))

    assert ack == {"ok": True, "players": ["Ada"]}
    assert broadcaster.entered == [("sid-host", game.code)]


def test_starting_the_game_is_announced_to_the_room():
    registry = GameRegistry()
    game = registry.create_game()
    registry.join(game.code, "Ada")
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.start_game(
        "sid-host", {"code": game.code, "host_token": game.host_token}
    ))

    assert ack == {"ok": True}
    assert broadcaster.emitted == [("game_started", game.code, {})]


def test_only_the_host_can_start_the_game_over_the_socket():
    registry = GameRegistry()
    game = registry.create_game()
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.start_game(
        "sid-player", {"code": game.code, "host_token": "not-the-host-token"}
    ))

    assert ack == {"ok": False, "error": "not_host"}
    assert broadcaster.emitted == []


def test_a_draw_is_announced_to_the_room_with_its_explanation():
    registry = GameRegistry()
    game = registry.create_game()
    registry.join(game.code, "Ada")
    registry.start(game.host_link)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.draw_topic(
        "sid-host", {"code": game.code, "host_token": game.host_token}
    ))

    draw = registry.draw_history(game.code)[0]
    expected = {
        "position": 1,
        "name": draw.topic.name,
        "explanation": draw.topic.explanation,
    }
    assert ack == {"ok": True, "draw": expected}
    assert broadcaster.emitted == [("topic_drawn", game.code, expected)]


def test_a_draw_before_the_game_starts_is_refused_to_the_sender_only():
    registry = GameRegistry()
    game = registry.create_game()
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.draw_topic(
        "sid-host", {"code": game.code, "host_token": game.host_token}
    ))

    assert ack == {"ok": False, "error": "not_started"}
    assert broadcaster.emitted == []

