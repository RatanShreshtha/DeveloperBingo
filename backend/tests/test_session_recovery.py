"""A client that reloads or reconnects gets the whole game back in one snapshot, and a player who
reloads can take their name over from a socket the server has not yet noticed dropping."""

from helpers import RealtimeTable, host_message, run, topics_on, wire_board_of

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.prizes import Prize

# --- the snapshot, as the wire carries it (its content is tested in test_game_snapshot.py) ---


def test_a_join_acknowledgement_carries_the_players_whole_snapshot():
    t = RealtimeTable()
    ada = t.ready_to_claim(whole_ticket=True)
    t.claim(prize="top_line")
    t.claim()
    close_top_line, close_early_five = t.scheduler.pending
    run(close_early_five())  # top line's window stays open
    run(t.adapter.disconnect("sid-ada"))

    ack = t.join("sid-ada-2")

    assert ack["ok"] is True
    assert ack["status"] == "started"
    assert ack["end_reason"] is None
    assert ack["players"] == ["Ada"]
    assert len(ack["draws"]) == len(DEFAULT_POOL.topics)
    assert set(ack["draws"][0]) == {"position", "name", "explanation"}
    assert ack["prizes"] == wire_board_of(early_five=["Ada"])
    assert ack["name"] == "Ada"
    assert ack["ticket"] == ada["ticket"]
    assert ack["ticks"] == sorted(topics_on(ada["ticket"]))
    assert ack["pending_claims"] == ["top_line"]
    assert ack["decided_claims"] == [
        {"prize": "early_five", "accepted": True, "error": None}
    ]
    assert ack["rejoin_token"] not in ("", ada["rejoin_token"])


def test_a_watch_acknowledgement_carries_the_hosts_whole_snapshot():
    t = RealtimeTable()
    t.ready_to_claim(whole_ticket=True)
    t.claim()

    ack = run(t.adapter.watch_lobby("sid-host", host_message(t.game)))

    assert ack["ok"] is True
    assert ack["status"] == "started"
    assert ack["players"] == ["Ada"]
    assert ack["prizes"] == wire_board_of()
    assert ack["claims"] == []
    assert ack["window_open"] is True
    assert ack["pool_name"] == "Default"
    assert sum(len(column) for column in ack["pool"]["columns"]) == len(
        DEFAULT_POOL.topics
    )


# --- the rejoin token ---


def test_the_first_join_returns_a_rejoin_token_and_a_rejoin_returns_a_new_one():
    t = RealtimeTable()
    first = t.join()
    run(t.adapter.disconnect("sid-ada"))

    second = t.join("sid-ada-2")

    assert first["rejoin_token"]
    assert second["rejoin_token"] and second["rejoin_token"] != first["rejoin_token"]


def test_the_right_token_takes_the_name_over_while_the_old_socket_is_still_connected():
    t = RealtimeTable()
    first = t.join()
    t.registry.start(t.game)

    second = t.join("sid-ada-2", rejoin_token=first["rejoin_token"])

    assert second["ok"] is True
    assert second["ticket"] == first["ticket"]
    assert t.broadcaster.left == [("sid-ada", t.game.code)]
    assert ("replaced", "sid-ada", {}) in t.broadcaster.emitted


def test_the_replaced_socket_no_longer_acts_for_the_player():
    t = RealtimeTable()
    first = t.join()
    t.start_and_draw_everything()
    t.join("sid-ada-2", rejoin_token=first["rejoin_token"])

    ack = run(t.adapter.tick_topic("sid-ada", {"topic": topics_on(first["ticket"])[0]}))

    assert ack == {"ok": False, "error": "not_joined"}


def test_the_replaced_sockets_late_disconnect_does_not_drop_the_new_one():
    t = RealtimeTable()
    first = t.join()
    t.start_and_draw_everything()
    t.join("sid-ada-2", rejoin_token=first["rejoin_token"])

    run(t.adapter.disconnect("sid-ada"))
    ack = run(
        t.adapter.tick_topic("sid-ada-2", {"topic": topics_on(first["ticket"])[0]})
    )

    assert ack == {"ok": True}
    assert t.join("sid-ada-3")["error"] == "name_taken"


def test_a_connected_name_is_refused_without_the_token():
    t = RealtimeTable()
    t.join()

    ack = t.join("sid-ada-2")

    assert ack == {"ok": False, "error": "name_taken"}


def test_a_connected_name_is_refused_with_a_wrong_token():
    t = RealtimeTable()
    t.join()

    ack = t.join("sid-ada-2", rejoin_token="not-the-token")

    assert ack == {"ok": False, "error": "name_taken"}
    assert t.broadcaster.left == []


def test_a_token_replaced_by_a_newer_join_no_longer_works():
    t = RealtimeTable()
    first = t.join()
    t.join("sid-ada-2", rejoin_token=first["rejoin_token"])

    ack = t.join("sid-ada-3", rejoin_token=first["rejoin_token"])

    assert ack == {"ok": False, "error": "name_taken"}


def test_a_dropped_player_still_rejoins_by_name_alone_and_with_a_wrong_token():
    t = RealtimeTable()
    t.join()
    run(t.adapter.disconnect("sid-ada"))

    assert t.join("sid-ada-2", rejoin_token="stale")["ok"] is True


def test_a_takeover_does_not_announce_a_change_to_the_lobby():
    t = RealtimeTable()
    first = t.join()
    before = len(t.broadcaster.emitted)

    t.join("sid-ada-2", rejoin_token=first["rejoin_token"])

    assert [e for e in t.broadcaster.emitted[before:] if e[0] == "lobby_updated"] == []


def settled_to(broadcaster):
    return [
        (target, data)
        for event, target, data in broadcaster.emitted
        if event == "claim_settled"
    ]


def test_a_takeover_during_a_pending_claim_sends_the_result_to_the_new_socket_only():
    # The client used to claim again after a rejoin to get its answer back; a window closing in
    # between made that a false `prize_taken` refusal in the host's log. Nothing is claimed again now.
    t = RealtimeTable()
    ada = t.ready_to_claim(whole_ticket=True)
    t.claim()

    takeover = t.join("sid-ada-2", rejoin_token=ada["rejoin_token"])
    t.scheduler.close_all()

    assert takeover["pending_claims"] == ["early_five"]
    assert settled_to(t.broadcaster) == [
        ("sid-ada-2", {"prize": "early_five", "accepted": True, "error": None})
    ]
    claims = t.registry.host_snapshot(t.game).claims
    assert [(entry.player, entry.accepted) for entry in claims] == [("Ada", True)]


def window_events(broadcaster):
    return [data for _, _, data in broadcaster.window_changes]


def test_the_host_is_told_when_a_window_opens_and_when_the_last_one_closes():
    t = RealtimeTable()
    t.ready_to_claim(whole_ticket=True)

    t.claim()
    opened = list(window_events(t.broadcaster))
    t.scheduler.close_all()

    assert opened == [{"open": True}]
    assert window_events(t.broadcaster) == [{"open": True}, {"open": False}]
    assert {room for _, room, _ in t.broadcaster.window_changes} == {
        f"{t.game.code}:host"
    }


# --- one handle per player: the name the engine stored, whatever the client typed ---


def test_a_join_tells_the_player_the_name_the_game_stored():
    t = RealtimeTable()

    assert t.join(name="  Ada ")["name"] == "Ada"


def test_a_rejoin_by_another_case_is_told_the_name_first_stored():
    t = RealtimeTable()
    t.join()
    run(t.adapter.disconnect("sid-ada"))

    assert t.join("sid-ada-2", name="ada")["name"] == "Ada"


def test_a_claim_by_a_player_who_joined_with_spaces_is_answered():
    t = RealtimeTable()
    t.ready_to_claim(name="Ada ", whole_ticket=True)

    t.claim()
    t.scheduler.close_all()

    assert settled_to(t.broadcaster) == [
        ("sid-ada", {"prize": "early_five", "accepted": True, "error": None})
    ]
    assert t.registry.host_snapshot(t.game).prizes[Prize.EARLY_FIVE] == ("Ada",)


def test_a_claim_waiting_through_a_takeover_by_another_case_is_answered():
    t = RealtimeTable()
    ada = t.ready_to_claim(whole_ticket=True)
    t.claim()

    t.join("sid-ada-2", name="ada", rejoin_token=ada["rejoin_token"])
    t.scheduler.close_all()

    assert settled_to(t.broadcaster) == [
        ("sid-ada-2", {"prize": "early_five", "accepted": True, "error": None})
    ]


def test_a_takeover_by_another_case_replaces_the_old_socket():
    t = RealtimeTable()
    ada = t.join()

    t.join("sid-ada-2", name="ADA", rejoin_token=ada["rejoin_token"])

    assert [
        target for event, target, _ in t.broadcaster.emitted if event == "replaced"
    ] == ["sid-ada"]
    assert t.broadcaster.left == [("sid-ada", t.game.code)]
