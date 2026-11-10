import asyncio

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

    assert ack == {"ok": True}
    assert registry.lobby(game.code, game.host_token) == ["Ada"]
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
