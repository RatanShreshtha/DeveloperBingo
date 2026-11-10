import asyncio
import random

from devbingo_backend.game import GameRegistry, PlayerRef
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
    registry.join(PlayerRef(game.code, "Ada"))
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.join_game("sid-2", {"code": game.code, "name": "Ada"}))

    assert ack == {"ok": False, "error": "name_taken"}
    assert broadcaster.emitted == []
    assert broadcaster.entered == []


def test_the_host_can_watch_the_lobby_with_the_host_token():
    registry = GameRegistry()
    game = registry.create_game()
    registry.join(PlayerRef(game.code, "Ada"))
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.watch_lobby(
        "sid-host", {"code": game.code, "host_token": game.host_token}
    ))

    assert ack["ok"] is True
    assert ack["players"] == ["Ada"]
    assert ack["prizes"] == {"early_five": None}
    assert broadcaster.entered == [("sid-host", game.code)]


def test_starting_the_game_is_announced_to_the_room():
    registry = GameRegistry()
    game = registry.create_game()
    registry.join(PlayerRef(game.code, "Ada"))
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
    registry.join(PlayerRef(game.code, "Ada"))
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


def started_game_with_every_topic_drawn():
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game()
    ticket = registry.join(PlayerRef(game.code, "Ada"))
    registry.start(game.host_link)
    for _ in range(90):
        registry.draw(game.host_link)
    return registry, game, ticket


def test_a_tick_is_acknowledged_without_sending_any_ticks_back():
    registry, game, ticket = started_game_with_every_topic_drawn()
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)
    topic = next(cell for line in ticket.to_cells() for cell in line if cell)

    ack = run(adapter.tick_topic("sid-ada", {"code": game.code, "name": "Ada", "topic": topic}))

    assert ack == {"ok": True}
    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset({topic})
    assert broadcaster.emitted == []


def test_an_untick_is_acknowledged_without_sending_any_ticks_back():
    registry, game, ticket = started_game_with_every_topic_drawn()
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())
    topic = next(cell for line in ticket.to_cells() for cell in line if cell)
    run(adapter.tick_topic("sid-ada", {"code": game.code, "name": "Ada", "topic": topic}))

    ack = run(adapter.untick_topic("sid-ada", {"code": game.code, "name": "Ada", "topic": topic}))

    assert ack == {"ok": True}
    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset()


def test_an_untick_of_a_topic_not_on_the_ticket_is_refused():
    registry, game, ticket = started_game_with_every_topic_drawn()
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())
    on_ticket = {cell for line in ticket.to_cells() for cell in line if cell}
    off_ticket = next(name for name in ("Pi", "Zero-day", "Yak shaving") if name not in on_ticket)

    ack = run(adapter.untick_topic("sid-ada", {"code": game.code, "name": "Ada", "topic": off_ticket}))

    assert ack == {"ok": False, "error": "not_on_ticket"}


def test_a_refused_tick_names_the_reason_and_changes_nothing():
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game()
    ticket = registry.join(PlayerRef(game.code, "Ada"))
    registry.start(game.host_link)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)
    topic = next(cell for line in ticket.to_cells() for cell in line if cell)

    ack = run(adapter.tick_topic("sid-ada", {"code": game.code, "name": "Ada", "topic": topic}))

    assert ack == {"ok": False, "error": "not_drawn"}
    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset()
    assert broadcaster.emitted == []


def test_a_dropped_player_can_rejoin_and_gets_their_ticket_and_ticks_back():
    registry = GameRegistry(rng=random.Random(9))
    game = registry.create_game()
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())
    first = run(adapter.join_game("sid-1", {"code": game.code, "name": "Ada"}))
    run(adapter.disconnect("sid-1"))

    rejoined = run(adapter.join_game("sid-2", {"code": game.code, "name": "Ada"}))

    assert rejoined["ok"] is True
    assert rejoined["ticket"] == first["ticket"]
    assert rejoined["ticks"] == []



def test_a_disconnect_from_an_unknown_session_does_nothing():
    registry = GameRegistry()
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())

    assert run(adapter.disconnect("sid-never-joined")) is None


def test_a_second_join_on_the_same_socket_is_refused_and_frees_nothing():
    registry = GameRegistry(rng=random.Random(9))
    game = registry.create_game()
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())
    run(adapter.join_game("sid-1", {"code": game.code, "name": "Ada"}))

    ack = run(adapter.join_game("sid-1", {"code": game.code, "name": "Grace"}))

    assert ack == {"ok": False, "error": "already_joined"}
    assert registry.players(game.code) == ["Ada"]


def test_a_socket_that_joined_twice_does_not_lock_its_first_player_out():
    registry = GameRegistry(rng=random.Random(9))
    game = registry.create_game()
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())
    run(adapter.join_game("sid-1", {"code": game.code, "name": "Ada"}))
    run(adapter.join_game("sid-1", {"code": game.code, "name": "Grace"}))

    run(adapter.disconnect("sid-1"))
    rejoined = run(adapter.join_game("sid-2", {"code": game.code, "name": "Ada"}))

    assert rejoined["ok"] is True


def test_a_rejoin_does_not_announce_a_change_to_the_lobby():
    registry = GameRegistry(rng=random.Random(9))
    game = registry.create_game()
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)
    run(adapter.join_game("sid-1", {"code": game.code, "name": "Ada"}))
    run(adapter.disconnect("sid-1"))

    run(adapter.join_game("sid-2", {"code": game.code, "name": "Ada"}))

    lobby_updates = [event for event in broadcaster.emitted if event[0] == "lobby_updated"]
    assert len(lobby_updates) == 1


def started_game_with_five_ticks_for_ada():
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game()
    ticket = registry.join(PlayerRef(game.code, "Ada"))
    registry.start(game.host_link)
    for _ in range(90):
        registry.draw(game.host_link)
    topics = sorted({cell.name for line in ticket.lines for cell in line if cell})
    for topic in topics[:5]:
        registry.tick(PlayerRef(game.code, "Ada"), topic)
    return registry, game


def test_a_valid_claim_is_acknowledged_and_announced_to_the_room():
    registry, game = started_game_with_five_ticks_for_ada()
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.claim_prize("sid-ada", {"code": game.code, "name": "Ada", "prize": "early_five"}))

    assert ack == {"ok": True}
    assert broadcaster.emitted == [
        ("prize_awarded", game.code, {"prize": "early_five", "winner": "Ada"}),
    ]


def test_a_refused_claim_is_told_to_the_claimant_only():
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game()
    registry.join(PlayerRef(game.code, "Ada"))
    registry.start(game.host_link)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.claim_prize("sid-ada", {"code": game.code, "name": "Ada", "prize": "early_five"}))

    assert ack == {"ok": False, "error": "not_won"}
    assert broadcaster.emitted == []


def test_a_second_claim_for_an_awarded_prize_is_refused():
    registry, game = started_game_with_five_ticks_for_ada()
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())
    run(adapter.claim_prize("sid-ada", {"code": game.code, "name": "Ada", "prize": "early_five"}))

    ack = run(adapter.claim_prize("sid-ada", {"code": game.code, "name": "Ada", "prize": "early_five"}))

    assert ack == {"ok": False, "error": "prize_taken"}


def test_an_unknown_prize_is_refused():
    registry, game = started_game_with_five_ticks_for_ada()
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())

    ack = run(adapter.claim_prize("sid-ada", {"code": game.code, "name": "Ada", "prize": "jackpot"}))

    assert ack == {"ok": False, "error": "unknown_prize"}


def test_the_join_acknowledgement_shows_which_prizes_remain():
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game()
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())

    ack = run(adapter.join_game("sid-ada", {"code": game.code, "name": "Ada"}))

    assert ack["prizes"] == {"early_five": None}
