import asyncio
import random
from dataclasses import dataclass

from helpers import start_and_draw_everything
from test_realtime import RecordingBroadcaster, claim_message, host_message, tick_message, topics_on

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry, PlayerRef
from devbingo_backend.realtime import DEFAULT_WINDOW_SECONDS, RealtimeAdapter


class ManualScheduler:
    """Holds the closes the adapter schedules, so a test fires them with no waiting."""

    def __init__(self) -> None:
        self.scheduled: list = []
        self.delays: list[float] = []

    def call_later(self, delay, action) -> None:
        self.delays.append(delay)
        self.scheduled.append(action)

    async def fire_all(self) -> None:
        scheduled, self.scheduled = self.scheduled, []
        for action in scheduled:
            await action()


@dataclass
class Table:
    adapter: RealtimeAdapter
    registry: GameRegistry
    game: object
    broadcaster: RecordingBroadcaster
    scheduler: ManualScheduler
    tickets: dict[str, list]


def table(window_seconds=DEFAULT_WINDOW_SECONDS) -> Table:
    """Ada and Grace have joined, the game has started, every topic is drawn and each has ticked five."""
    registry = GameRegistry(rng=random.Random(5))
    game = registry.create_game(DEFAULT_POOL)
    broadcaster = RecordingBroadcaster()
    scheduler = ManualScheduler()
    adapter = RealtimeAdapter(registry, broadcaster, scheduler=scheduler, window_seconds=window_seconds)
    tickets: dict[str, list] = {}

    async def setup():
        for name in ("Ada", "Grace"):
            ack = await adapter.join_game(f"sid-{name.lower()}", {"code": game.code, "name": name})
            tickets[name] = ack["ticket"]
        start_and_draw_everything(registry, game)
        for name, cells in tickets.items():
            for topic in topics_on(cells)[:5]:
                await adapter.tick_topic(f"sid-{name.lower()}", tick_message(game, topic, name))

    asyncio.run(setup())
    return Table(adapter, registry, game, broadcaster, scheduler, tickets)


async def settle_soon():
    """Let held claims reach the point where they wait for their window."""
    for _ in range(3):
        await asyncio.sleep(0)


def claim_task(t, sid, name, prize="early_five"):
    return asyncio.create_task(t.adapter.claim_prize(sid, claim_message(t.game, name, prize)))


def claims_then_close(t, claimants, prize="early_five"):
    """Each (sid, name) claims in turn; the claims are held until the window closes."""

    async def scenario():
        tasks = [claim_task(t, sid, name, prize) for sid, name in claimants]
        await settle_soon()
        held = [task.done() for task in tasks]
        await t.scheduler.fire_all()
        return held, [await task for task in tasks]

    return asyncio.run(scenario())


def emitted(t, *events):
    return [e for e in t.broadcaster.emitted if e[0] in events]


ADA_AND_GRACE = [("sid-ada", "Ada"), ("sid-grace", "Grace")]


def test_the_window_is_scheduled_once_with_the_configured_length():
    t = table(window_seconds=2.5)

    claims_then_close(t, ADA_AND_GRACE)

    assert t.scheduler.delays == [2.5]


def test_the_window_length_defaults_to_one_second():
    assert DEFAULT_WINDOW_SECONDS == 1.0


def test_each_claimants_acknowledgement_is_held_until_the_window_settles():
    t = table()

    held, acks = claims_then_close(t, ADA_AND_GRACE)

    assert held == [False, False]
    assert acks == [{"ok": True}, {"ok": True}]


def test_every_winner_is_broadcast_once_at_close():
    t = table()

    claims_then_close(t, ADA_AND_GRACE)

    assert emitted(t, "prize_awarded") == [
        ("prize_awarded", t.game.code, {"prize": "early_five", "awarded_to": ["Ada", "Grace"]})
    ]


def test_nothing_is_announced_while_the_window_is_open():
    t = table()

    async def scenario():
        task = claim_task(t, "sid-ada", "Ada")
        await settle_soon()
        announced = emitted(t, "prize_awarded")
        await t.scheduler.fire_all()
        await task
        return announced

    assert asyncio.run(scenario()) == []


def test_a_draw_is_refused_while_a_window_is_open():
    t = table()

    async def scenario():
        task = claim_task(t, "sid-ada", "Ada")
        await settle_soon()
        during = await t.adapter.draw_topic("sid-host", host_message(t.game))
        await t.scheduler.fire_all()
        await task
        after = await t.adapter.draw_topic("sid-host", host_message(t.game))
        return during, after

    during, after = asyncio.run(scenario())

    assert during == {"ok": False, "error": "settlement_open"}
    # Once it closes the hold is gone: every topic is already drawn, so the pool refuses instead.
    assert after == {"ok": False, "error": "no_topics_left"}


def test_an_untick_is_refused_while_the_claim_is_pending():
    t = table()
    topic = sorted(t.registry.ticks(PlayerRef(t.game.code, "Ada")))[0]

    async def scenario():
        task = claim_task(t, "sid-ada", "Ada")
        await settle_soon()
        refused = await t.adapter.untick_topic("sid-ada", tick_message(t.game, topic))
        await t.scheduler.fire_all()
        await task
        allowed = await t.adapter.untick_topic("sid-ada", tick_message(t.game, topic))
        return refused, allowed

    refused, allowed = asyncio.run(scenario())

    assert refused == {"ok": False, "error": "claim_pending"}
    assert allowed == {"ok": True}


def test_a_queued_claim_that_fails_at_close_is_refused_to_that_claimant_only():
    t = table()
    grace_topics = sorted(t.registry.ticks(PlayerRef(t.game.code, "Grace")))

    async def scenario():
        # Grace has taken back two ticks, so only Ada's claim is valid; hers still queues in the window.
        for topic in grace_topics[:2]:
            await t.adapter.untick_topic("sid-grace", tick_message(t.game, topic, "Grace"))
        ada = claim_task(t, "sid-ada", "Ada")
        await settle_soon()
        grace = claim_task(t, "sid-grace", "Grace")
        await settle_soon()
        await t.scheduler.fire_all()
        return await ada, await grace

    ada_ack, grace_ack = asyncio.run(scenario())

    assert ada_ack == {"ok": True}
    assert grace_ack == {"ok": False, "error": "claim_not_valid"}
    assert emitted(t, "prize_awarded") == [
        ("prize_awarded", t.game.code, {"prize": "early_five", "awarded_to": ["Ada"]})
    ]


def test_the_host_is_told_of_each_claim_when_it_settles_not_before():
    t = table()

    async def scenario():
        await t.adapter.watch_lobby("sid-host", host_message(t.game))
        task = claim_task(t, "sid-ada", "Ada")
        await settle_soon()
        before = emitted(t, "claim_logged")
        await t.scheduler.fire_all()
        await task
        return before

    before = asyncio.run(scenario())

    assert before == []
    assert emitted(t, "claim_logged") == [
        ("claim_logged", f"{t.game.code}:host",
         {"player": "Ada", "prize": "early_five", "accepted": True, "error": None})
    ]


def test_a_repeat_claim_in_the_window_is_answered_at_close_without_a_second_window():
    t = table()

    held, acks = claims_then_close(t, [("sid-ada", "Ada"), ("sid-ada", "Ada")])

    assert held == [False, False]
    assert acks == [{"ok": True}, {"ok": True}]
    assert t.scheduler.delays == [DEFAULT_WINDOW_SECONDS]


def test_a_full_house_window_ends_the_game_once_for_every_winner():
    t = table()

    async def scenario():
        for name, cells in t.tickets.items():
            for topic in topics_on(cells):
                await t.adapter.tick_topic(f"sid-{name.lower()}", tick_message(t.game, topic, name))

    asyncio.run(scenario())

    _, acks = claims_then_close(t, ADA_AND_GRACE, prize="full_house")

    assert acks == [{"ok": True}, {"ok": True}]
    assert emitted(t, "prize_awarded", "game_ended") == [
        ("prize_awarded", t.game.code, {"prize": "full_house", "awarded_to": ["Ada", "Grace"]}),
        ("game_ended", t.game.code, {"reason": "full_house"}),
    ]
