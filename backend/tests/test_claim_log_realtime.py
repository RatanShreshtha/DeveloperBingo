from helpers import ManualScheduler
from test_realtime import (
    RecordingBroadcaster,
    claim_and_close,
    claim_message,
    host_message,
    run,
    started_game_with_five_ticks_for_ada,
    to_room,
)


def watch_as_host(adapter, game, sid="sid-host"):
    return run(adapter.watch_lobby(sid, host_message(game)))


def test_the_host_is_told_of_a_refused_claim_and_the_players_are_not():
    broadcaster = RecordingBroadcaster()
    adapter, _, game = started_game_with_five_ticks_for_ada(broadcaster)
    watch_as_host(adapter, game)
    in_the_room_before = to_room(broadcaster, game.code)
    ack = run(adapter.claim_prize("sid-ada", claim_message(game, prize="full_house")))

    # The claimant is told by the acknowledgement alone: a refusal never becomes `claim_settled`.
    assert ack["error"] == "claim_not_valid"
    assert [e for e in broadcaster.emitted if e[0] == "claim_settled"] == []

    host_events = [event for event in broadcaster.emitted if event[0] == "claim_logged"]
    # A refused claim is private: no event of any kind reaches the room the players are in.
    assert to_room(broadcaster, game.code) == in_the_room_before

    assert host_events == [(
        "claim_logged", f"{game.code}:host",
        {"player": "Ada", "prize": "full_house", "accepted": False, "error": "claim_not_valid"},
    )]
    assert ("sid-host", f"{game.code}:host") in broadcaster.entered
    assert ("sid-ada", f"{game.code}:host") not in broadcaster.entered


def test_the_host_is_told_of_an_accepted_claim_as_well_as_the_room():
    broadcaster, scheduler = RecordingBroadcaster(), ManualScheduler()
    adapter, _, game = started_game_with_five_ticks_for_ada(broadcaster, scheduler)

    claim_and_close(adapter, scheduler, game)

    assert [e for e in broadcaster.emitted if e[1] == f"{game.code}:host"] == [
        ("claim_logged", f"{game.code}:host",
         {"player": "Ada", "prize": "early_five", "accepted": True, "error": None})
    ]
    assert [e for e in to_room(broadcaster, game.code) if e[0] == "claim_logged"] == []


def test_a_malformed_claim_or_one_from_a_socket_that_never_joined_is_not_logged():
    broadcaster = RecordingBroadcaster()
    adapter, registry, game = started_game_with_five_ticks_for_ada(broadcaster)

    run(adapter.claim_prize("sid-stranger", claim_message(game)))
    run(adapter.claim_prize("sid-ada", {"prize": 5}))
    run(adapter.claim_prize("sid-ada", claim_message(game, prize="jackpot")))

    assert registry.host_snapshot(game).claims == ()
    assert [e for e in broadcaster.emitted if e[0] == "claim_logged"] == []


def test_a_host_who_reconnects_gets_the_claims_so_far_in_the_watch_acknowledgement():
    scheduler = ManualScheduler()
    adapter, _, game = started_game_with_five_ticks_for_ada(scheduler=scheduler)
    run(adapter.claim_prize("sid-ada", claim_message(game, prize="full_house")))
    claim_and_close(adapter, scheduler, game)

    ack = watch_as_host(adapter, game, sid="sid-host-after-reconnect")

    assert ack["claims"] == [
        {"player": "Ada", "prize": "full_house", "accepted": False, "error": "claim_not_valid"},
        {"player": "Ada", "prize": "early_five", "accepted": True, "error": None},
    ]
