from helpers import (
    RealtimeTable,
    claim_message,
    host_message,
    run,
    tick_message,
    topics_on,
    wire_board_of,
)

from devbingo_backend.game import PlayerRef
from devbingo_backend.prizes import Prize


def test_a_join_becomes_an_engine_command_and_a_room_broadcast():
    t = RealtimeTable()

    ack = run(t.adapter.join_game("sid-1", {"code": t.game.code, "name": "Ada"}))

    assert ack["ok"] is True
    assert len(ack["ticket"]) == 3
    assert all(len(line) == 9 for line in ack["ticket"])
    assert t.registry.host_snapshot(t.game).players == ("Ada",)
    assert t.broadcaster.entered == [("sid-1", t.game.code)]
    assert t.broadcaster.emitted == [
        ("lobby_updated", t.game.code, {"players": ["Ada"]}),
    ]


def test_a_rejected_join_is_acknowledged_to_the_sender_only():
    t = RealtimeTable()
    t.registry.join(PlayerRef(t.game.code, "Ada"))

    ack = run(t.adapter.join_game("sid-2", {"code": t.game.code, "name": "Ada"}))

    assert ack == {"ok": False, "error": "name_taken"}
    assert t.broadcaster.emitted == []
    assert t.broadcaster.entered == []


def test_the_host_can_watch_the_lobby_with_the_host_token():
    t = RealtimeTable()
    t.registry.join(PlayerRef(t.game.code, "Ada"))

    ack = run(
        t.adapter.watch_lobby(
            "sid-host", {"code": t.game.code, "host_token": t.game.host_token}
        )
    )

    assert ack["ok"] is True
    assert ack["players"] == ["Ada"]
    assert ack["prizes"] == wire_board_of()
    assert ack["claims"] == []
    # The second room is host-only, where claims are told that players must not see.
    assert t.broadcaster.entered == [
        ("sid-host", t.game.code),
        ("sid-host", f"{t.game.code}:host"),
    ]


def test_starting_the_game_is_announced_to_the_room():
    t = RealtimeTable()
    t.registry.join(PlayerRef(t.game.code, "Ada"))

    ack = run(
        t.adapter.start_game(
            "sid-host", {"code": t.game.code, "host_token": t.game.host_token}
        )
    )

    assert ack == {"ok": True}
    assert t.broadcaster.emitted == [("game_started", t.game.code, {})]


def test_only_the_host_can_start_the_game_over_the_socket():
    t = RealtimeTable()

    ack = run(
        t.adapter.start_game(
            "sid-player", {"code": t.game.code, "host_token": "not-the-host-token"}
        )
    )

    assert ack == {"ok": False, "error": "not_host"}
    assert t.broadcaster.emitted == []


def test_a_draw_is_announced_to_the_room_with_its_explanation():
    t = RealtimeTable()
    t.registry.join(PlayerRef(t.game.code, "Ada"))
    t.registry.start(t.game)

    ack = run(
        t.adapter.draw_topic(
            "sid-host", {"code": t.game.code, "host_token": t.game.host_token}
        )
    )

    draw = t.registry.host_snapshot(t.game).draws[0]
    expected = {
        "position": 1,
        "name": draw.topic.name,
        "explanation": draw.topic.explanation,
    }
    assert ack == {"ok": True, "draw": expected}
    assert t.broadcaster.emitted == [("topic_drawn", t.game.code, expected)]


def test_a_draw_before_the_game_starts_is_refused_to_the_sender_only():
    t = RealtimeTable()

    ack = run(
        t.adapter.draw_topic(
            "sid-host", {"code": t.game.code, "host_token": t.game.host_token}
        )
    )

    assert ack == {"ok": False, "error": "not_started"}
    assert t.broadcaster.emitted == []


def test_a_tick_is_acknowledged_without_sending_any_ticks_back():
    t = RealtimeTable()
    cells = t.join()["ticket"]
    t.start_and_draw_everything()
    topic = topics_on(cells)[0]
    emitted_before = list(t.broadcaster.emitted)

    ack = run(t.adapter.tick_topic("sid-ada", tick_message(t.game, topic)))

    assert ack == {"ok": True}
    assert t.registry.player_snapshot(PlayerRef(t.game.code, "Ada")).ticks == frozenset(
        {topic}
    )
    assert t.broadcaster.emitted == emitted_before


def test_an_untick_is_acknowledged_without_sending_any_ticks_back():
    t = RealtimeTable()
    cells = t.join()["ticket"]
    t.start_and_draw_everything()
    topic = topics_on(cells)[0]
    run(t.adapter.tick_topic("sid-ada", tick_message(t.game, topic)))

    ack = run(t.adapter.untick_topic("sid-ada", tick_message(t.game, topic)))

    assert ack == {"ok": True}
    assert (
        t.registry.player_snapshot(PlayerRef(t.game.code, "Ada")).ticks == frozenset()
    )


def test_an_untick_of_a_topic_not_on_the_ticket_is_refused():
    t = RealtimeTable()
    cells = t.join()["ticket"]
    t.start_and_draw_everything()
    on_ticket = set(topics_on(cells))
    off_ticket = next(
        name for name in ("Pi", "Zero-day", "Yak shaving") if name not in on_ticket
    )

    ack = run(t.adapter.untick_topic("sid-ada", tick_message(t.game, off_ticket)))

    assert ack == {"ok": False, "error": "not_on_ticket"}


def test_a_refused_tick_names_the_reason_and_changes_nothing():
    t = RealtimeTable(seed=5)
    joined = run(t.adapter.join_game("sid-ada", {"code": t.game.code, "name": "Ada"}))
    t.registry.start(t.game)
    emitted_before = list(t.broadcaster.emitted)

    ack = run(
        t.adapter.tick_topic(
            "sid-ada", tick_message(t.game, topics_on(joined["ticket"])[0])
        )
    )

    assert ack == {"ok": False, "error": "not_drawn"}
    assert (
        t.registry.player_snapshot(PlayerRef(t.game.code, "Ada")).ticks == frozenset()
    )
    assert t.broadcaster.emitted == emitted_before


def test_a_dropped_player_can_rejoin_and_gets_their_ticket_and_ticks_back():
    t = RealtimeTable(seed=9)
    first = run(t.adapter.join_game("sid-1", {"code": t.game.code, "name": "Ada"}))
    run(t.adapter.disconnect("sid-1"))

    rejoined = run(t.adapter.join_game("sid-2", {"code": t.game.code, "name": "Ada"}))

    assert rejoined["ok"] is True
    assert rejoined["ticket"] == first["ticket"]
    assert rejoined["ticks"] == []


def test_a_disconnect_from_an_unknown_session_does_nothing():
    t = RealtimeTable()

    assert run(t.adapter.disconnect("sid-never-joined")) is None


def test_a_second_join_on_the_same_socket_is_refused_and_frees_nothing():
    t = RealtimeTable(seed=9)
    run(t.adapter.join_game("sid-1", {"code": t.game.code, "name": "Ada"}))

    ack = run(t.adapter.join_game("sid-1", {"code": t.game.code, "name": "Grace"}))

    assert ack == {"ok": False, "error": "already_joined"}
    assert t.registry.host_snapshot(t.game).players == ("Ada",)


def test_a_socket_that_joined_twice_does_not_lock_its_first_player_out():
    t = RealtimeTable(seed=9)
    run(t.adapter.join_game("sid-1", {"code": t.game.code, "name": "Ada"}))
    run(t.adapter.join_game("sid-1", {"code": t.game.code, "name": "Grace"}))

    run(t.adapter.disconnect("sid-1"))
    rejoined = run(t.adapter.join_game("sid-2", {"code": t.game.code, "name": "Ada"}))

    assert rejoined["ok"] is True


def test_a_rejoin_does_not_announce_a_change_to_the_lobby():
    t = RealtimeTable(seed=9)
    run(t.adapter.join_game("sid-1", {"code": t.game.code, "name": "Ada"}))
    run(t.adapter.disconnect("sid-1"))
    emitted_before = list(t.broadcaster.emitted)

    run(t.adapter.join_game("sid-2", {"code": t.game.code, "name": "Ada"}))

    assert t.broadcaster.emitted == emitted_before


WAITING = {"ok": True, "waiting": True}


def test_a_valid_claim_waits_then_is_announced_to_the_room_and_settled_for_the_claimant():
    t = RealtimeTable()
    t.ready_to_claim()

    ack = t.claim_and_close()

    assert ack == WAITING
    assert t.to_room()[-1] == (
        "prize_awarded",
        t.game.code,
        {"prize": "early_five", "awarded_to": ["Ada"]},
    )
    assert t.settled_for() == [{"prize": "early_five", "accepted": True, "error": None}]


def test_a_valid_claim_for_a_new_prize_is_announced_to_the_room():
    t = RealtimeTable()
    cells = t.join()["ticket"]
    t.start_and_draw_everything()
    for topic in sorted(name for name in cells[0] if name):
        run(t.adapter.tick_topic("sid-ada", tick_message(t.game, topic)))

    ack = t.claim_and_close(prize="top_line")

    assert ack == WAITING
    assert t.to_room()[-1] == (
        "prize_awarded",
        t.game.code,
        {"prize": "top_line", "awarded_to": ["Ada"]},
    )


def test_an_incomplete_full_house_claim_is_refused_and_not_announced():
    t = RealtimeTable()
    t.ready_to_claim()
    emitted_before = t.to_room()

    ack = run(
        t.adapter.claim_prize("sid-ada", claim_message(t.game, prize="full_house"))
    )

    assert ack == {"ok": False, "error": "claim_not_valid"}
    assert t.to_room() == emitted_before


def test_a_refused_claim_is_told_to_the_claimant_only():
    t = RealtimeTable(seed=5)
    run(t.adapter.join_game("sid-ada", {"code": t.game.code, "name": "Ada"}))
    t.registry.start(t.game)
    emitted_before = t.to_room()

    ack = run(t.adapter.claim_prize("sid-ada", claim_message(t.game)))

    assert ack == {"ok": False, "error": "claim_not_valid"}
    assert t.to_room() == emitted_before


def test_a_second_claim_for_an_awarded_prize_is_refused():
    t = RealtimeTable()
    t.ready_to_claim()
    t.claim_and_close()

    ack = run(t.adapter.claim_prize("sid-ada", claim_message(t.game)))

    assert ack == {"ok": False, "error": "prize_taken"}


def test_an_unknown_prize_is_refused():
    t = RealtimeTable()
    t.ready_to_claim()

    ack = run(t.adapter.claim_prize("sid-ada", claim_message(t.game, prize="jackpot")))

    assert ack == {"ok": False, "error": "unknown_prize"}


def test_the_join_acknowledgement_shows_which_prizes_remain():
    t = RealtimeTable(seed=5)

    ack = run(t.adapter.join_game("sid-ada", {"code": t.game.code, "name": "Ada"}))

    assert ack["prizes"] == wire_board_of()


def test_a_socket_that_never_joined_is_refused_a_claim_and_nothing_changes():
    t = RealtimeTable()
    t.ready_to_claim()
    emitted_before = list(t.broadcaster.emitted)

    ack = run(t.adapter.claim_prize("sid-stranger", claim_message(t.game)))

    assert ack == {"ok": False, "error": "not_joined"}
    assert t.registry.host_snapshot(t.game).prizes[Prize.EARLY_FIVE] == ()
    assert t.broadcaster.emitted == emitted_before


def test_a_socket_that_never_joined_cannot_tick_or_untick():
    t = RealtimeTable()
    cells = t.join()["ticket"]
    t.start_and_draw_everything()
    message = tick_message(t.game, topics_on(cells)[0])

    ticked = run(t.adapter.tick_topic("sid-stranger", message))
    unticked = run(t.adapter.untick_topic("sid-stranger", message))

    assert ticked == {"ok": False, "error": "not_joined"}
    assert unticked == {"ok": False, "error": "not_joined"}
    assert (
        t.registry.player_snapshot(PlayerRef(t.game.code, "Ada")).ticks == frozenset()
    )


def test_a_player_cannot_tick_as_another_player_by_naming_them_in_the_message():
    t = RealtimeTable()
    ada_cells = t.join()["ticket"]
    t.join_players("Grace")
    t.start_and_draw_everything()
    topic = topics_on(ada_cells)[0]

    # Grace's socket says it is Ada. Whatever happens, Ada's ticks must not change.
    run(t.adapter.tick_topic("sid-grace", tick_message(t.game, topic, name="Ada")))

    assert (
        t.registry.player_snapshot(PlayerRef(t.game.code, "Ada")).ticks == frozenset()
    )


def test_a_player_cannot_untick_another_player_by_naming_them_in_the_message():
    t = RealtimeTable()
    ada_cells = t.join()["ticket"]
    t.join_players("Grace")
    t.start_and_draw_everything()
    topic = topics_on(ada_cells)[0]
    run(t.adapter.tick_topic("sid-ada", tick_message(t.game, topic)))

    run(t.adapter.untick_topic("sid-grace", tick_message(t.game, topic, name="Ada")))

    assert t.registry.player_snapshot(PlayerRef(t.game.code, "Ada")).ticks == frozenset(
        {topic}
    )


def test_a_claim_is_judged_on_the_socket_s_player_not_the_name_in_the_message():
    t = RealtimeTable()
    ada_cells = t.join()["ticket"]
    t.join_players("Grace")
    t.start_and_draw_everything()
    for topic in topics_on(ada_cells)[:5]:
        run(t.adapter.tick_topic("sid-ada", tick_message(t.game, topic)))

    # Grace has ticked nothing, so claiming "as Ada" from her socket must fail.
    ack = run(t.adapter.claim_prize("sid-grace", claim_message(t.game, name="Ada")))

    assert ack == {"ok": False, "error": "claim_not_valid"}
    assert t.registry.host_snapshot(t.game).prizes[Prize.EARLY_FIVE] == ()


def test_a_join_with_a_missing_field_is_refused_as_an_invalid_message():
    t = RealtimeTable()

    ack = run(t.adapter.join_game("sid-1", {"code": t.game.code}))

    assert ack == {"ok": False, "error": "invalid_message"}
    assert t.registry.host_snapshot(t.game).players == ()
    assert t.broadcaster.emitted == []


def test_a_host_command_with_no_token_is_refused_as_an_invalid_message():
    t = RealtimeTable()

    for command in (t.adapter.watch_lobby, t.adapter.start_game, t.adapter.draw_topic):
        assert run(command("sid-host", {"code": t.game.code})) == {
            "ok": False,
            "error": "invalid_message",
        }


def test_a_tick_or_claim_with_a_missing_or_wrong_typed_field_is_refused_as_an_invalid_message():
    t = RealtimeTable()
    t.join()
    t.start_and_draw_everything()

    assert run(t.adapter.tick_topic("sid-ada", {})) == {
        "ok": False,
        "error": "invalid_message",
    }
    assert run(t.adapter.untick_topic("sid-ada", {"topic": 7})) == {
        "ok": False,
        "error": "invalid_message",
    }
    assert run(t.adapter.claim_prize("sid-ada", {})) == {
        "ok": False,
        "error": "invalid_message",
    }
    assert (
        t.registry.player_snapshot(PlayerRef(t.game.code, "Ada")).ticks == frozenset()
    )


def test_a_payload_that_is_not_an_object_is_refused_as_an_invalid_message():
    t = RealtimeTable()
    t.join()
    t.start_and_draw_everything()

    assert run(t.adapter.tick_topic("sid-ada", None)) == {
        "ok": False,
        "error": "invalid_message",
    }


def test_the_host_ending_the_game_is_announced_to_the_room():
    t = RealtimeTable()
    t.join()
    t.start_and_draw_everything()

    ack = run(t.adapter.end_game("sid-host", host_message(t.game)))

    assert ack == {"ok": True}
    assert t.broadcaster.emitted[-1] == ("game_ended", t.game.code, {"reason": "host"})


def test_only_the_host_can_end_the_game_over_the_socket():
    t = RealtimeTable()
    t.join()
    t.start_and_draw_everything()
    emitted_before = list(t.broadcaster.emitted)

    ack = run(
        t.adapter.end_game(
            "sid-ada", {"code": t.game.code, "host_token": "not-the-host-token"}
        )
    )

    assert ack == {"ok": False, "error": "not_host"}
    assert t.broadcaster.emitted == emitted_before


def test_ending_a_game_twice_is_refused_and_announces_nothing_more():
    t = RealtimeTable()
    t.join()
    t.start_and_draw_everything()
    run(t.adapter.end_game("sid-host", host_message(t.game)))
    emitted_before = list(t.broadcaster.emitted)

    ack = run(t.adapter.end_game("sid-host", host_message(t.game)))

    assert ack == {"ok": False, "error": "game_ended"}
    assert t.broadcaster.emitted == emitted_before


def test_claiming_the_full_house_ends_the_game_and_tells_the_room():
    t = RealtimeTable()
    cells = t.join()["ticket"]
    t.start_and_draw_everything()
    for topic in topics_on(cells):
        run(t.adapter.tick_topic("sid-ada", tick_message(t.game, topic)))

    ack = t.claim_and_close(prize="full_house")

    assert ack == WAITING
    assert t.to_room()[-2:] == [
        ("prize_awarded", t.game.code, {"prize": "full_house", "awarded_to": ["Ada"]}),
        ("game_ended", t.game.code, {"reason": "full_house"}),
    ]


def test_a_claim_for_another_prize_does_not_end_the_game():
    t = RealtimeTable()
    t.ready_to_claim()

    run(t.adapter.claim_prize("sid-ada", claim_message(t.game)))

    assert [event for event in t.broadcaster.emitted if event[0] == "game_ended"] == []


def test_draws_and_claims_are_refused_after_the_game_ends():
    t = RealtimeTable()
    t.ready_to_claim()
    run(t.adapter.end_game("sid-host", host_message(t.game)))

    draw = run(t.adapter.draw_topic("sid-host", host_message(t.game)))
    claim = run(t.adapter.claim_prize("sid-ada", claim_message(t.game)))

    assert draw == {"ok": False, "error": "game_ended"}
    assert claim == {"ok": False, "error": "game_ended"}
    assert t.registry.host_snapshot(t.game).prizes[Prize.EARLY_FIVE] == ()


def test_a_dropped_player_can_rejoin_a_game_that_has_ended_and_read_the_result():
    t = RealtimeTable()
    t.join()
    t.start_and_draw_everything()
    run(t.adapter.disconnect("sid-ada"))
    run(t.adapter.end_game("sid-host", host_message(t.game)))

    ack = run(t.adapter.join_game("sid-ada-2", {"code": t.game.code, "name": "Ada"}))

    assert ack["ok"] is True
    assert ack["status"] == "ended"
    assert ack["end_reason"] == "host"
    assert len(ack["draws"]) == 90
