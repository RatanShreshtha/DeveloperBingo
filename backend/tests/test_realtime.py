import asyncio
import random

from helpers import start_and_draw_everything, wire_board_of

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry, PlayerRef
from devbingo_backend.prizes import Prize
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


def to_room(broadcaster, code):
    """What was emitted to the game's room, where every player is. The host-only room is left out."""
    return [event for event in broadcaster.emitted if event[1] == code]


def run(coro):
    return asyncio.run(coro)


def test_a_join_becomes_an_engine_command_and_a_room_broadcast():
    registry = GameRegistry()
    game = registry.create_game(DEFAULT_POOL)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.join_game("sid-1", {"code": game.code, "name": "Ada"}))

    assert ack["ok"] is True
    assert len(ack["ticket"]) == 3
    assert all(len(line) == 9 for line in ack["ticket"])
    assert registry.lobby(game) == ["Ada"]
    assert broadcaster.entered == [("sid-1", game.code)]
    assert broadcaster.emitted == [
        ("lobby_updated", game.code, {"players": ["Ada"]}),
    ]


def test_a_rejected_join_is_acknowledged_to_the_sender_only():
    registry = GameRegistry()
    game = registry.create_game(DEFAULT_POOL)
    registry.join(PlayerRef(game.code, "Ada"))
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.join_game("sid-2", {"code": game.code, "name": "Ada"}))

    assert ack == {"ok": False, "error": "name_taken"}
    assert broadcaster.emitted == []
    assert broadcaster.entered == []


def test_the_host_can_watch_the_lobby_with_the_host_token():
    registry = GameRegistry()
    game = registry.create_game(DEFAULT_POOL)
    registry.join(PlayerRef(game.code, "Ada"))
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.watch_lobby(
        "sid-host", {"code": game.code, "host_token": game.host_token}
    ))

    assert ack["ok"] is True
    assert ack["players"] == ["Ada"]
    assert ack["prizes"] == wire_board_of()
    assert ack["claims"] == []
    # The second room is host-only, where claims are told that players must not see.
    assert broadcaster.entered == [("sid-host", game.code), ("sid-host", f"{game.code}:host")]


def test_starting_the_game_is_announced_to_the_room():
    registry = GameRegistry()
    game = registry.create_game(DEFAULT_POOL)
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
    game = registry.create_game(DEFAULT_POOL)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.start_game(
        "sid-player", {"code": game.code, "host_token": "not-the-host-token"}
    ))

    assert ack == {"ok": False, "error": "not_host"}
    assert broadcaster.emitted == []


def test_a_draw_is_announced_to_the_room_with_its_explanation():
    registry = GameRegistry()
    game = registry.create_game(DEFAULT_POOL)
    registry.join(PlayerRef(game.code, "Ada"))
    registry.start(game)
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
    game = registry.create_game(DEFAULT_POOL)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.draw_topic(
        "sid-host", {"code": game.code, "host_token": game.host_token}
    ))

    assert ack == {"ok": False, "error": "not_started"}
    assert broadcaster.emitted == []


def started_game_with_every_topic_drawn(broadcaster=None):
    """A started game with every topic drawn. Ada joined on socket "sid-ada"."""
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game(DEFAULT_POOL)
    adapter = RealtimeAdapter(registry, broadcaster or RecordingBroadcaster())
    joined = run(adapter.join_game("sid-ada", {"code": game.code, "name": "Ada"}))
    start_and_draw_everything(registry, game)
    return adapter, registry, game, joined["ticket"]


def topics_on(cells):
    return sorted({cell for line in cells for cell in line if cell})


def tick_message(game, topic, name="Ada"):
    return {"code": game.code, "name": name, "topic": topic}


def test_a_tick_is_acknowledged_without_sending_any_ticks_back():
    broadcaster = RecordingBroadcaster()
    adapter, registry, game, cells = started_game_with_every_topic_drawn(broadcaster)
    topic = topics_on(cells)[0]
    emitted_before = list(broadcaster.emitted)

    ack = run(adapter.tick_topic("sid-ada", tick_message(game, topic)))

    assert ack == {"ok": True}
    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset({topic})
    assert broadcaster.emitted == emitted_before


def test_an_untick_is_acknowledged_without_sending_any_ticks_back():
    adapter, registry, game, cells = started_game_with_every_topic_drawn()
    topic = topics_on(cells)[0]
    run(adapter.tick_topic("sid-ada", tick_message(game, topic)))

    ack = run(adapter.untick_topic("sid-ada", tick_message(game, topic)))

    assert ack == {"ok": True}
    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset()


def test_an_untick_of_a_topic_not_on_the_ticket_is_refused():
    adapter, registry, game, cells = started_game_with_every_topic_drawn()
    on_ticket = set(topics_on(cells))
    off_ticket = next(name for name in ("Pi", "Zero-day", "Yak shaving") if name not in on_ticket)

    ack = run(adapter.untick_topic("sid-ada", tick_message(game, off_ticket)))

    assert ack == {"ok": False, "error": "not_on_ticket"}


def test_a_refused_tick_names_the_reason_and_changes_nothing():
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game(DEFAULT_POOL)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)
    joined = run(adapter.join_game("sid-ada", {"code": game.code, "name": "Ada"}))
    registry.start(game)
    emitted_before = list(broadcaster.emitted)

    ack = run(adapter.tick_topic("sid-ada", tick_message(game, topics_on(joined["ticket"])[0])))

    assert ack == {"ok": False, "error": "not_drawn"}
    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset()
    assert broadcaster.emitted == emitted_before


def test_a_dropped_player_can_rejoin_and_gets_their_ticket_and_ticks_back():
    registry = GameRegistry(rng=random.Random(9))
    game = registry.create_game(DEFAULT_POOL)
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
    game = registry.create_game(DEFAULT_POOL)
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())
    run(adapter.join_game("sid-1", {"code": game.code, "name": "Ada"}))

    ack = run(adapter.join_game("sid-1", {"code": game.code, "name": "Grace"}))

    assert ack == {"ok": False, "error": "already_joined"}
    assert registry.players(game.code) == ["Ada"]


def test_a_socket_that_joined_twice_does_not_lock_its_first_player_out():
    registry = GameRegistry(rng=random.Random(9))
    game = registry.create_game(DEFAULT_POOL)
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())
    run(adapter.join_game("sid-1", {"code": game.code, "name": "Ada"}))
    run(adapter.join_game("sid-1", {"code": game.code, "name": "Grace"}))

    run(adapter.disconnect("sid-1"))
    rejoined = run(adapter.join_game("sid-2", {"code": game.code, "name": "Ada"}))

    assert rejoined["ok"] is True


def test_a_rejoin_does_not_announce_a_change_to_the_lobby():
    registry = GameRegistry(rng=random.Random(9))
    game = registry.create_game(DEFAULT_POOL)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)
    run(adapter.join_game("sid-1", {"code": game.code, "name": "Ada"}))
    run(adapter.disconnect("sid-1"))
    emitted_before = list(broadcaster.emitted)

    run(adapter.join_game("sid-2", {"code": game.code, "name": "Ada"}))

    assert broadcaster.emitted == emitted_before


def started_game_with_five_ticks_for_ada(broadcaster=None):
    adapter, registry, game, cells = started_game_with_every_topic_drawn(broadcaster)
    for topic in topics_on(cells)[:5]:
        run(adapter.tick_topic("sid-ada", tick_message(game, topic)))
    return adapter, registry, game


def claim_message(game, name="Ada", prize="early_five"):
    return {"code": game.code, "name": name, "prize": prize}


def test_a_valid_claim_is_acknowledged_and_announced_to_the_room():
    broadcaster = RecordingBroadcaster()
    adapter, _, game = started_game_with_five_ticks_for_ada(broadcaster)

    ack = run(adapter.claim_prize("sid-ada", claim_message(game)))

    assert ack == {"ok": True}
    assert broadcaster.emitted[-1] == ("prize_awarded", game.code, {"prize": "early_five", "awarded_to": ["Ada"]})


def test_a_valid_claim_for_a_new_prize_is_acknowledged_and_announced_to_the_room():
    broadcaster = RecordingBroadcaster()
    adapter, _, game, cells = started_game_with_every_topic_drawn(broadcaster)
    for topic in sorted(name for name in cells[0] if name):
        run(adapter.tick_topic("sid-ada", tick_message(game, topic)))

    ack = run(adapter.claim_prize("sid-ada", claim_message(game, prize="top_line")))

    assert ack == {"ok": True}
    assert broadcaster.emitted[-1] == ("prize_awarded", game.code, {"prize": "top_line", "awarded_to": ["Ada"]})


def test_an_incomplete_full_house_claim_is_refused_and_not_announced():
    broadcaster = RecordingBroadcaster()
    adapter, _, game = started_game_with_five_ticks_for_ada(broadcaster)
    emitted_before = to_room(broadcaster, game.code)

    ack = run(adapter.claim_prize("sid-ada", claim_message(game, prize="full_house")))

    assert ack == {"ok": False, "error": "claim_not_valid"}
    assert to_room(broadcaster, game.code) == emitted_before


def test_a_refused_claim_is_told_to_the_claimant_only():
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game(DEFAULT_POOL)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)
    run(adapter.join_game("sid-ada", {"code": game.code, "name": "Ada"}))
    registry.start(game)
    emitted_before = to_room(broadcaster, game.code)

    ack = run(adapter.claim_prize("sid-ada", claim_message(game)))

    assert ack == {"ok": False, "error": "claim_not_valid"}
    assert to_room(broadcaster, game.code) == emitted_before


def test_a_second_claim_for_an_awarded_prize_is_refused():
    adapter, _, game = started_game_with_five_ticks_for_ada()
    run(adapter.claim_prize("sid-ada", claim_message(game)))

    ack = run(adapter.claim_prize("sid-ada", claim_message(game)))

    assert ack == {"ok": False, "error": "prize_taken"}


def test_an_unknown_prize_is_refused():
    adapter, _, game = started_game_with_five_ticks_for_ada()

    ack = run(adapter.claim_prize("sid-ada", claim_message(game, prize="jackpot")))

    assert ack == {"ok": False, "error": "unknown_prize"}


def test_the_join_acknowledgement_shows_which_prizes_remain():
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game(DEFAULT_POOL)
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())

    ack = run(adapter.join_game("sid-ada", {"code": game.code, "name": "Ada"}))

    assert ack["prizes"] == wire_board_of()


def test_a_socket_that_never_joined_is_refused_a_claim_and_nothing_changes():
    broadcaster = RecordingBroadcaster()
    adapter, registry, game = started_game_with_five_ticks_for_ada(broadcaster)
    emitted_before = list(broadcaster.emitted)

    ack = run(adapter.claim_prize("sid-stranger", claim_message(game)))

    assert ack == {"ok": False, "error": "not_joined"}
    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == []
    assert broadcaster.emitted == emitted_before


def test_a_socket_that_never_joined_cannot_tick_or_untick():
    adapter, registry, game, cells = started_game_with_every_topic_drawn()
    message = tick_message(game, topics_on(cells)[0])

    ticked = run(adapter.tick_topic("sid-stranger", message))
    unticked = run(adapter.untick_topic("sid-stranger", message))

    assert ticked == {"ok": False, "error": "not_joined"}
    assert unticked == {"ok": False, "error": "not_joined"}
    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset()


def lobby_of_ada_and_grace():
    """Ada and Grace joined on their own sockets, the game started, every topic drawn."""
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game(DEFAULT_POOL)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)
    ada = run(adapter.join_game("sid-ada", {"code": game.code, "name": "Ada"}))
    run(adapter.join_game("sid-grace", {"code": game.code, "name": "Grace"}))
    start_and_draw_everything(registry, game)
    return adapter, registry, game, ada["ticket"]


def test_a_player_cannot_tick_as_another_player_by_naming_them_in_the_message():
    adapter, registry, game, ada_cells = lobby_of_ada_and_grace()
    topic = topics_on(ada_cells)[0]

    # Grace's socket says it is Ada. Whatever happens, Ada's ticks must not change.
    run(adapter.tick_topic("sid-grace", tick_message(game, topic, name="Ada")))

    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset()


def test_a_player_cannot_untick_another_player_by_naming_them_in_the_message():
    adapter, registry, game, ada_cells = lobby_of_ada_and_grace()
    topic = topics_on(ada_cells)[0]
    run(adapter.tick_topic("sid-ada", tick_message(game, topic)))

    run(adapter.untick_topic("sid-grace", tick_message(game, topic, name="Ada")))

    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset({topic})


def test_a_claim_is_judged_on_the_socket_s_player_not_the_name_in_the_message():
    adapter, registry, game, ada_cells = lobby_of_ada_and_grace()
    for topic in topics_on(ada_cells)[:5]:
        run(adapter.tick_topic("sid-ada", tick_message(game, topic)))

    # Grace has ticked nothing, so claiming "as Ada" from her socket must fail.
    ack = run(adapter.claim_prize("sid-grace", claim_message(game, name="Ada")))

    assert ack == {"ok": False, "error": "claim_not_valid"}
    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == []


def test_a_join_with_a_missing_field_is_refused_as_an_invalid_message():
    registry = GameRegistry()
    game = registry.create_game(DEFAULT_POOL)
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)

    ack = run(adapter.join_game("sid-1", {"code": game.code}))

    assert ack == {"ok": False, "error": "invalid_message"}
    assert registry.players(game.code) == []
    assert broadcaster.emitted == []


def test_a_host_command_with_no_token_is_refused_as_an_invalid_message():
    registry = GameRegistry()
    game = registry.create_game(DEFAULT_POOL)
    adapter = RealtimeAdapter(registry, RecordingBroadcaster())

    for command in (adapter.watch_lobby, adapter.start_game, adapter.draw_topic):
        assert run(command("sid-host", {"code": game.code})) == {"ok": False, "error": "invalid_message"}


def test_a_tick_or_claim_with_a_missing_or_wrong_typed_field_is_refused_as_an_invalid_message():
    adapter, registry, game, cells = started_game_with_every_topic_drawn()

    assert run(adapter.tick_topic("sid-ada", {})) == {"ok": False, "error": "invalid_message"}
    assert run(adapter.untick_topic("sid-ada", {"topic": 7})) == {"ok": False, "error": "invalid_message"}
    assert run(adapter.claim_prize("sid-ada", {})) == {"ok": False, "error": "invalid_message"}
    assert registry.ticks(PlayerRef(game.code, "Ada")) == frozenset()


def test_a_payload_that_is_not_an_object_is_refused_as_an_invalid_message():
    adapter, _, _, _ = started_game_with_every_topic_drawn()

    assert run(adapter.tick_topic("sid-ada", None)) == {"ok": False, "error": "invalid_message"}



def host_message(game):
    return {"code": game.code, "host_token": game.host_token}


def test_the_host_ending_the_game_is_announced_to_the_room():
    broadcaster = RecordingBroadcaster()
    adapter, registry, game, _ = started_game_with_every_topic_drawn(broadcaster)

    ack = run(adapter.end_game("sid-host", host_message(game)))

    assert ack == {"ok": True}
    assert broadcaster.emitted[-1] == ("game_ended", game.code, {"reason": "host"})


def test_only_the_host_can_end_the_game_over_the_socket():
    broadcaster = RecordingBroadcaster()
    adapter, registry, game, _ = started_game_with_every_topic_drawn(broadcaster)
    emitted_before = list(broadcaster.emitted)

    ack = run(adapter.end_game("sid-ada", {"code": game.code, "host_token": "not-the-host-token"}))

    assert ack == {"ok": False, "error": "not_host"}
    assert broadcaster.emitted == emitted_before


def test_ending_a_game_twice_is_refused_and_announces_nothing_more():
    broadcaster = RecordingBroadcaster()
    adapter, registry, game, _ = started_game_with_every_topic_drawn(broadcaster)
    run(adapter.end_game("sid-host", host_message(game)))
    emitted_before = list(broadcaster.emitted)

    ack = run(adapter.end_game("sid-host", host_message(game)))

    assert ack == {"ok": False, "error": "game_ended"}
    assert broadcaster.emitted == emitted_before


def test_claiming_the_full_house_ends_the_game_and_tells_the_room():
    broadcaster = RecordingBroadcaster()
    adapter, registry, game, cells = started_game_with_every_topic_drawn(broadcaster)
    for topic in topics_on(cells):
        run(adapter.tick_topic("sid-ada", tick_message(game, topic)))

    ack = run(adapter.claim_prize("sid-ada", claim_message(game, prize="full_house")))

    assert ack == {"ok": True}
    assert broadcaster.emitted[-2:] == [
        ("prize_awarded", game.code, {"prize": "full_house", "awarded_to": ["Ada"]}),
        ("game_ended", game.code, {"reason": "full_house"}),
    ]


def test_a_claim_for_another_prize_does_not_end_the_game():
    broadcaster = RecordingBroadcaster()
    adapter, _, game = started_game_with_five_ticks_for_ada(broadcaster)

    run(adapter.claim_prize("sid-ada", claim_message(game)))

    assert [event for event in broadcaster.emitted if event[0] == "game_ended"] == []


def test_draws_and_claims_are_refused_after_the_game_ends():
    adapter, registry, game = started_game_with_five_ticks_for_ada()
    run(adapter.end_game("sid-host", host_message(game)))

    draw = run(adapter.draw_topic("sid-host", host_message(game)))
    claim = run(adapter.claim_prize("sid-ada", claim_message(game)))

    assert draw == {"ok": False, "error": "game_ended"}
    assert claim == {"ok": False, "error": "game_ended"}
    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == []


def test_a_dropped_player_cannot_rejoin_a_game_that_has_ended():
    adapter, registry, game, _ = started_game_with_every_topic_drawn()
    run(adapter.disconnect("sid-ada"))
    run(adapter.end_game("sid-host", host_message(game)))

    ack = run(adapter.join_game("sid-ada-2", {"code": game.code, "name": "Ada"}))

    assert ack == {"ok": False, "error": "game_ended"}
