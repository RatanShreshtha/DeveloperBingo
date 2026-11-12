"""A client that reloads or reconnects gets the whole game back in one snapshot, and a player who
reloads can take their name over from a socket the server has not yet noticed dropping."""

import asyncio
import random

from helpers import start_and_draw_everything, wire_board_of
from test_realtime import RecordingBroadcaster, host_message, run, topics_on

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry
from devbingo_backend.prizes import Prize
from devbingo_backend.realtime import RealtimeAdapter


class ManualScheduler:
    """Keeps closes until the test asks for them."""

    def __init__(self) -> None:
        self.pending: list = []

    def call_later(self, delay, action) -> None:
        self.pending.append(action)

    def close_all(self) -> None:
        for action in self.pending:
            run(action())
        self.pending = []


def a_game(scheduler=None):
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game(DEFAULT_POOL, pool_name="Default")
    broadcaster = RecordingBroadcaster()
    adapter = RealtimeAdapter(registry, broadcaster, scheduler, window_seconds=0)
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


def test_the_hosts_snapshot_says_while_a_settlement_window_is_open():
    scheduler = ManualScheduler()
    adapter, registry, game, _ = a_game(scheduler)
    ada = join(adapter, game)
    start_and_draw_everything(registry, game)
    for topic in topics_on(ada["ticket"]):
        run(adapter.tick_topic("sid-ada", {"topic": topic}))

    async def claim_then_watch():
        claim = asyncio.ensure_future(adapter.claim_prize("sid-ada", {"prize": "early_five"}))
        await asyncio.sleep(0)
        watched = await adapter.watch_lobby("sid-host", host_message(game))
        for action in scheduler.pending:
            await action()
        await claim
        return watched

    watched = asyncio.run(claim_then_watch())

    assert watched["window_open"] is True


def test_a_reconnect_inside_a_settlement_window_says_which_claims_are_pending():
    scheduler = ManualScheduler()
    adapter, registry, game, _ = a_game(scheduler)
    ada = join(adapter, game)
    start_and_draw_everything(registry, game)
    for topic in topics_on(ada["ticket"]):
        run(adapter.tick_topic("sid-ada", {"topic": topic}))

    async def scenario():
        claim = asyncio.ensure_future(adapter.claim_prize("sid-ada", {"prize": "early_five"}))
        await asyncio.sleep(0)
        await adapter.disconnect("sid-ada")
        snapshot = await adapter.join_game("sid-ada-2", {"code": game.code, "name": "Ada"})
        for action in scheduler.pending:
            await action()
        await claim
        return snapshot

    snapshot = asyncio.run(scenario())

    assert snapshot["pending_claims"] == ["early_five"]


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


def test_a_takeover_during_a_pending_claim_reattaches_it_without_logging_it_twice():
    scheduler = ManualScheduler()
    adapter, registry, game, _ = a_game(scheduler)
    ada = join(adapter, game)
    start_and_draw_everything(registry, game)
    for topic in topics_on(ada["ticket"]):
        run(adapter.tick_topic("sid-ada", {"topic": topic}))

    async def scenario():
        first_claim = asyncio.ensure_future(adapter.claim_prize("sid-ada", {"prize": "early_five"}))
        await asyncio.sleep(0)
        takeover = await adapter.join_game(
            "sid-ada-2", {"code": game.code, "name": "Ada", "rejoin_token": ada["rejoin_token"]}
        )
        reattached = asyncio.ensure_future(adapter.claim_prize("sid-ada-2", {"prize": "early_five"}))
        await asyncio.sleep(0)
        for action in scheduler.pending:
            await action()
        return takeover, await first_claim, await reattached

    takeover, first, second = asyncio.run(scenario())

    assert takeover["pending_claims"] == ["early_five"]
    assert first == {"ok": True}
    assert second == {"ok": True}
    assert [entry.player for entry in registry.claim_log(game.code)] == ["Ada"]
