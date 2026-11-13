from helpers import RealtimeTable, claim_message, run


def test_the_host_is_told_of_a_refused_claim_and_the_players_are_not():
    t = RealtimeTable()
    t.ready_to_claim()
    t.watch()
    in_the_room_before = t.to_room()
    ack = t.claim(prize="full_house")

    # The claimant is told by the acknowledgement alone: a refusal never becomes `claim_settled`.
    assert ack["error"] == "claim_not_valid"
    assert [e for e in t.broadcaster.emitted if e[0] == "claim_settled"] == []

    host_events = [
        event for event in t.broadcaster.emitted if event[0] == "claim_logged"
    ]
    # A refused claim is private: no event of any kind reaches the room the players are in.
    assert t.to_room() == in_the_room_before

    assert host_events == [
        (
            "claim_logged",
            t.host,
            {
                "player": "Ada",
                "prize": "full_house",
                "accepted": False,
                "error": "claim_not_valid",
            },
        )
    ]
    assert ("sid-host", t.host) in t.broadcaster.entered
    assert ("sid-ada", t.host) not in t.broadcaster.entered


def test_the_host_is_told_of_an_accepted_claim_as_well_as_the_room():
    t = RealtimeTable()
    t.ready_to_claim()

    t.claim_and_close()

    assert [e for e in t.broadcaster.emitted if e[1] == t.host] == [
        (
            "claim_logged",
            t.host,
            {"player": "Ada", "prize": "early_five", "accepted": True, "error": None},
        )
    ]
    assert [e for e in t.to_room() if e[0] == "claim_logged"] == []


def test_a_malformed_claim_or_one_from_a_socket_that_never_joined_is_not_logged():
    t = RealtimeTable()
    t.ready_to_claim()

    run(t.adapter.claim_prize("sid-stranger", claim_message(t.game)))
    run(t.adapter.claim_prize("sid-ada", {"prize": 5}))
    run(t.adapter.claim_prize("sid-ada", claim_message(t.game, prize="jackpot")))

    assert t.registry.host_snapshot(t.game).claims == ()
    assert [e for e in t.broadcaster.emitted if e[0] == "claim_logged"] == []


def test_a_host_who_reconnects_gets_the_claims_so_far_in_the_watch_acknowledgement():
    t = RealtimeTable()
    t.ready_to_claim()
    t.claim(prize="full_house")
    t.claim_and_close()

    ack = t.watch(sid="sid-host-after-reconnect")

    assert ack["claims"] == [
        {
            "player": "Ada",
            "prize": "full_house",
            "accepted": False,
            "error": "claim_not_valid",
        },
        {"player": "Ada", "prize": "early_five", "accepted": True, "error": None},
    ]
