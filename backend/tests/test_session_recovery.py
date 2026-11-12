"""A client that reloads or reconnects gets the whole game back in one snapshot, and a player who
reloads can take their name over from a socket the server has not yet noticed dropping."""

import random

from helpers import ManualScheduler, start_and_draw_everything, wire_board_of
from test_realtime import RecordingBroadcaster, host_message, run, topics_on

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry
from devbingo_backend.prizes import Prize
from devbingo_backend.realtime import RealtimeAdapter


def a_game(scheduler=None):
    registry = GameRegistry(rng=random.Random(5), scheduler=scheduler or ManualScheduler())
    game = registry.create_game(DEFAULT_POOL, pool_name="Default")
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster)
    return adapter, registry, game, broadcaster


def join(adapter, game, sid="sid-ada", name="Ada", **extra):
    return run(adapter.join_game(sid, {"code": game.code, "name": name, **extra}))


# --- the snapshot ---


def test_a_player_joining_a_game_in_the_lobby_gets_its_status_and_players():
    adapter, _, game, _ = a_game()
    join(adapter, game, "sid-grace", "Grace")

    ack = join(adapter, game)

    assert ack["status"] == "lobby"
    assert ack["end_reason"] is None
    assert ack["players"] == ["Grace", "Ada"]
    assert ack["draws"] == []
    assert ack["prizes"] == wire_board_of()
    assert ack["pending_claims"] == []


def test_a_rejoin_between_the_start_and_the_first_draw_knows_the_game_started():
    adapter, registry, game, _ = a_game()
    join(adapter, game)
    registry.start(game)
    run(adapter.disconnect("sid-ada"))

    ack = join(adapter, game, "sid-ada-2")

    assert ack["status"] == "started"
    assert ack["draws"] == []


def test_a_snapshot_carries_every_draw_in_order():
    adapter, registry, game, _ = a_game()
    join(adapter, game)
    registry.start(game)
    first, second = registry.draw(game), registry.draw(game)
    run(adapter.disconnect("sid-ada"))

    ack = join(adapter, game, "sid-ada-2")

    assert [draw["position"] for draw in ack["draws"]] == [1, 2]
    assert [draw["name"] for draw in ack["draws"]] == [first.topic.name, second.topic.name]
    assert all(draw["explanation"] for draw in ack["draws"])


def test_the_hosts_snapshot_carries_status_draws_pool_and_claim_log():
    adapter, registry, game, _ = a_game()
    join(adapter, game)
    registry.start(game)
    registry.draw(game)

    ack = run(adapter.watch_lobby("sid-host", host_message(game)))

    assert ack["ok"] is True
    assert ack["status"] == "started"
    assert ack["players"] == ["Ada"]
    assert len(ack["draws"]) == 1
    assert ack["claims"] == []
    assert ack["window_open"] is False
    assert ack["pool_name"] == "Default"
    assert sum(len(column) for column in ack["pool"]["columns"]) == len(DEFAULT_POOL.topics)


def test_a_snapshot_after_the_game_ends_says_why_and_shows_the_final_prize_board():
    adapter, registry, game, _ = a_game()
    join(adapter, game)
    registry.start(game)
    run(adapter.end_game("sid-host", host_message(game)))

    host = run(adapter.watch_lobby("sid-host-2", host_message(game)))

    assert host["status"] == "ended"
    assert host["end_reason"] == "host"
    assert host["prizes"] == wire_board_of()


def ready_to_claim(adapter, registry, game, sid="sid-ada", name="Ada"):
    """Ada has joined, every topic is drawn and she has ticked her whole ticket."""
    ada = join(adapter, game, sid, name)
    start_and_draw_everything(registry, game)
    for topic in topics_on(ada["ticket"]):
        run(adapter.tick_topic(sid, {"topic": topic}))
    return ada


def claim(adapter, sid="sid-ada", prize="early_five"):
    return run(adapter.claim_prize(sid, {"prize": prize}))


def test_the_hosts_snapshot_says_while_a_settlement_window_is_open():
    scheduler = ManualScheduler()
    adapter, registry, game, _ = a_game(scheduler)
    ready_to_claim(adapter, registry, game)
    claim(adapter)

    watched = run(adapter.watch_lobby("sid-host", host_message(game)))

    assert watched["window_open"] is True


def test_a_reconnect_inside_a_settlement_window_says_which_claims_are_pending():
    adapter, registry, game, _ = a_game()
    ready_to_claim(adapter, registry, game)
    claim(adapter)
    run(adapter.disconnect("sid-ada"))

    snapshot = join(adapter, game, "sid-ada-2")

    assert snapshot["pending_claims"] == ["early_five"]
    assert snapshot["decided_claims"] == []


def test_a_rejoin_after_the_window_closed_carries_the_players_decided_claims():
    scheduler = ManualScheduler()
    adapter, registry, game, _ = a_game(scheduler)
    ready_to_claim(adapter, registry, game)
    claim(adapter)
    run(adapter.disconnect("sid-ada"))
    scheduler.close_all()

    snapshot = join(adapter, game, "sid-ada-2")

    assert snapshot["pending_claims"] == []
    assert snapshot["decided_claims"] == [{"prize": "early_five", "accepted": True, "error": None}]


# --- the rejoin token ---


def test_the_first_join_returns_a_rejoin_token_and_a_rejoin_returns_a_new_one():
    adapter, _, game, _ = a_game()
    first = join(adapter, game)
    run(adapter.disconnect("sid-ada"))

    second = join(adapter, game, "sid-ada-2")

    assert first["rejoin_token"]
    assert second["rejoin_token"] and second["rejoin_token"] != first["rejoin_token"]


def test_the_right_token_takes_the_name_over_while_the_old_socket_is_still_connected():
    adapter, registry, game, broadcaster = a_game()
    first = join(adapter, game)
    registry.start(game)

    second = join(adapter, game, "sid-ada-2", rejoin_token=first["rejoin_token"])

    assert second["ok"] is True
    assert second["ticket"] == first["ticket"]
    assert broadcaster.left == [("sid-ada", game.code)]
    assert ("replaced", "sid-ada", {}) in broadcaster.emitted


def test_the_replaced_socket_no_longer_acts_for_the_player():
    adapter, registry, game, _ = a_game()
    first = join(adapter, game)
    start_and_draw_everything(registry, game)
    join(adapter, game, "sid-ada-2", rejoin_token=first["rejoin_token"])

    ack = run(adapter.tick_topic("sid-ada", {"topic": topics_on(first["ticket"])[0]}))

    assert ack == {"ok": False, "error": "not_joined"}


def test_the_replaced_sockets_late_disconnect_does_not_drop_the_new_one():
    adapter, registry, game, _ = a_game()
    first = join(adapter, game)
    start_and_draw_everything(registry, game)
    join(adapter, game, "sid-ada-2", rejoin_token=first["rejoin_token"])

    run(adapter.disconnect("sid-ada"))
    ack = run(adapter.tick_topic("sid-ada-2", {"topic": topics_on(first["ticket"])[0]}))

    assert ack == {"ok": True}
    assert join(adapter, game, "sid-ada-3")["error"] == "name_taken"


def test_a_connected_name_is_refused_without_the_token():
    adapter, _, game, _ = a_game()
    join(adapter, game)

    ack = join(adapter, game, "sid-ada-2")

    assert ack == {"ok": False, "error": "name_taken"}


def test_a_connected_name_is_refused_with_a_wrong_token():
    adapter, _, game, broadcaster = a_game()
    join(adapter, game)

    ack = join(adapter, game, "sid-ada-2", rejoin_token="not-the-token")

    assert ack == {"ok": False, "error": "name_taken"}
    assert broadcaster.left == []


def test_a_token_replaced_by_a_newer_join_no_longer_works():
    adapter, _, game, _ = a_game()
    first = join(adapter, game)
    join(adapter, game, "sid-ada-2", rejoin_token=first["rejoin_token"])

    ack = join(adapter, game, "sid-ada-3", rejoin_token=first["rejoin_token"])

    assert ack == {"ok": False, "error": "name_taken"}


def test_a_dropped_player_still_rejoins_by_name_alone_and_with_a_wrong_token():
    adapter, _, game, _ = a_game()
    join(adapter, game)
    run(adapter.disconnect("sid-ada"))

    assert join(adapter, game, "sid-ada-2", rejoin_token="stale")["ok"] is True


def test_a_takeover_does_not_announce_a_change_to_the_lobby():
    adapter, _, game, broadcaster = a_game()
    first = join(adapter, game)
    before = len(broadcaster.emitted)

    join(adapter, game, "sid-ada-2", rejoin_token=first["rejoin_token"])

    assert [e for e in broadcaster.emitted[before:] if e[0] == "lobby_updated"] == []


def settled_to(broadcaster):
    return [(target, data) for event, target, data in broadcaster.emitted if event == "claim_settled"]


def test_a_takeover_during_a_pending_claim_sends_the_result_to_the_new_socket_only():
    # The client used to claim again after a rejoin to get its answer back; a window closing in
    # between made that a false `prize_taken` refusal in the host's log. Nothing is claimed again now.
    scheduler = ManualScheduler()
    adapter, registry, game, broadcaster = a_game(scheduler)
    ada = ready_to_claim(adapter, registry, game)
    claim(adapter)

    takeover = join(adapter, game, "sid-ada-2", rejoin_token=ada["rejoin_token"])
    scheduler.close_all()

    assert takeover["pending_claims"] == ["early_five"]
    assert settled_to(broadcaster) == [
        ("sid-ada-2", {"prize": "early_five", "accepted": True, "error": None})
    ]
    assert [(entry.player, entry.accepted) for entry in registry.claim_log(game.code)] == [("Ada", True)]


def window_events(broadcaster):
    return [data for _, _, data in broadcaster.window_changes]


def test_the_host_is_told_when_a_window_opens_and_when_the_last_one_closes():
    scheduler = ManualScheduler()
    adapter, registry, game, broadcaster = a_game(scheduler)
    ready_to_claim(adapter, registry, game)

    claim(adapter)
    opened = list(window_events(broadcaster))
    scheduler.close_all()

    assert opened == [{"open": True}]
    assert window_events(broadcaster) == [{"open": True}, {"open": False}]
    assert {room for _, room, _ in broadcaster.window_changes} == {f"{game.code}:host"}


# --- one handle per player: the name the engine stored, whatever the client typed ---


def test_a_join_tells_the_player_the_name_the_game_stored():
    adapter, _, game, _ = a_game()

    assert join(adapter, game, name="  Ada ")["name"] == "Ada"


def test_a_rejoin_by_another_case_is_told_the_name_first_stored():
    adapter, _, game, _ = a_game()
    join(adapter, game)
    run(adapter.disconnect("sid-ada"))

    assert join(adapter, game, "sid-ada-2", name="ada")["name"] == "Ada"


def test_a_claim_by_a_player_who_joined_with_spaces_is_answered():
    scheduler = ManualScheduler()
    adapter, registry, game, broadcaster = a_game(scheduler)
    ready_to_claim(adapter, registry, game, name="Ada ")

    claim(adapter)
    scheduler.close_all()

    assert settled_to(broadcaster) == [("sid-ada", {"prize": "early_five", "accepted": True, "error": None})]
    assert registry.prize_board(game.code)[Prize.EARLY_FIVE] == ["Ada"]


def test_a_claim_waiting_through_a_takeover_by_another_case_is_answered():
    scheduler = ManualScheduler()
    adapter, registry, game, broadcaster = a_game(scheduler)
    ada = ready_to_claim(adapter, registry, game)
    claim(adapter)

    join(adapter, game, "sid-ada-2", name="ada", rejoin_token=ada["rejoin_token"])
    scheduler.close_all()

    assert settled_to(broadcaster) == [("sid-ada-2", {"prize": "early_five", "accepted": True, "error": None})]


def test_a_takeover_by_another_case_replaces_the_old_socket():
    adapter, _, game, broadcaster = a_game()
    ada = join(adapter, game)

    join(adapter, game, "sid-ada-2", name="ADA", rejoin_token=ada["rejoin_token"])

    assert [target for event, target, _ in broadcaster.emitted if event == "replaced"] == ["sid-ada"]
    assert broadcaster.left == [("sid-ada", game.code)]
