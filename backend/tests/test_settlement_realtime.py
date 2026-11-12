"""How the adapter announces settlement outcomes: what is sent, to whom, and in what order, and that
one failed send stops nothing else. When windows close, and who wins, is the engine's: see
test_settlement_clock.py and test_settlement_window.py."""

import asyncio
import logging
import random

from helpers import ManualScheduler, start_and_draw_everything
from test_realtime import host_message, run, tick_message, topics_on

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry, PlayerRef
from devbingo_backend.prizes import Prize
from devbingo_backend.realtime import RealtimeAdapter
from devbingo_backend.scheduler import AsyncioScheduler


class OrderedBroadcaster:
    """Records every emit in one list, in order, and raises for the events in `failing`."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, object]] = []
        self.failing: set[str] = set()

    async def enter_room(self, sid: str, room: str) -> None:
        pass

    async def leave_room(self, sid: str, room: str) -> None:
        pass

    async def emit(self, event, data, room=None, to=None) -> None:
        if event in self.failing:
            raise RuntimeError(f"cannot emit {event}")
        self.sent.append((event, room or to or "", data))


class Table:
    """Ada and Grace have joined on their own sockets, the host watches, every topic is drawn and
    each player has ticked five."""

    def __init__(self, scheduler=None) -> None:
        self.scheduler = scheduler or ManualScheduler()
        self.registry = GameRegistry(rng=random.Random(5), scheduler=self.scheduler, window_seconds=0)
        self.game = self.registry.create_game(DEFAULT_POOL)
        self.broadcaster = OrderedBroadcaster()
        self.adapter = RealtimeAdapter(self.registry, self.broadcaster)
        self.tickets: dict[str, list] = {}
        for name in ("Ada", "Grace"):
            ack = run(self.adapter.join_game(self.sid(name), {"code": self.game.code, "name": name}))
            self.tickets[name] = ack["ticket"]
        run(self.adapter.watch_lobby("sid-host", host_message(self.game)))
        start_and_draw_everything(self.registry, self.game)
        for name in ("Ada", "Grace"):
            self.tick(name, topics_on(self.tickets[name])[:5])
        self.broadcaster.sent.clear()

    @staticmethod
    def sid(name: str) -> str:
        return f"sid-{name.lower()}"

    def tick(self, name: str, topics) -> None:
        for topic in topics:
            run(self.adapter.tick_topic(self.sid(name), tick_message(self.game, topic, name)))

    def claim(self, name: str, prize: str = "early_five"):
        return run(self.adapter.claim_prize(self.sid(name), {"prize": prize}))

    @property
    def host(self) -> str:
        return f"{self.game.code}:host"


def logged(t, who, accepted=True, error=None, prize="early_five"):
    return ("claim_logged", t.host, {"player": who, "prize": prize, "accepted": accepted, "error": error})


def settled(t, who, accepted=True, error=None, prize="early_five"):
    return ("claim_settled", Table.sid(who), {"prize": prize, "accepted": accepted, "error": error})


def window(t, is_open):
    return ("window_changed", t.host, {"open": is_open})


def test_the_first_valid_claim_is_waiting_and_tells_the_host_the_window_opened():
    t = Table()

    acks = [t.claim("Ada"), t.claim("Grace")]

    assert acks == [{"ok": True, "waiting": True}] * 2
    assert t.broadcaster.sent == [window(t, True)]


def test_a_close_logs_each_claim_then_awards_then_tells_each_claimant_then_the_window():
    t = Table()
    t.claim("Ada")
    t.claim("Grace")
    t.broadcaster.sent.clear()

    t.scheduler.close_all()

    assert t.broadcaster.sent == [
        logged(t, "Ada"),
        logged(t, "Grace"),
        ("prize_awarded", t.game.code, {"prize": "early_five", "awarded_to": ["Ada", "Grace"]}),
        settled(t, "Ada"),
        settled(t, "Grace"),
        window(t, False),
    ]


def test_a_claim_refused_at_close_is_settled_for_that_claimant_only():
    t = Table()
    # Grace takes back two ticks, so her claim is not valid; it still queues in Ada's open window.
    grace_ticks = sorted(t.registry.ticks(PlayerRef(t.game.code, "Grace")))
    for topic in grace_ticks[:2]:
        run(t.adapter.untick_topic("sid-grace", tick_message(t.game, topic, "Grace")))
    t.claim("Ada")
    t.claim("Grace")
    t.broadcaster.sent.clear()

    t.scheduler.close_all()

    assert [e for e in t.broadcaster.sent if e[0] == "claim_settled"] == [
        settled(t, "Ada"),
        settled(t, "Grace", False, "claim_not_valid"),
    ]
    assert ("prize_awarded", t.game.code, {"prize": "early_five", "awarded_to": ["Ada"]}) in t.broadcaster.sent


def test_a_full_house_close_announces_the_end_before_telling_the_claimants():
    t = Table()
    for name in ("Ada", "Grace"):
        t.tick(name, topics_on(t.tickets[name]))
    t.claim("Ada", "full_house")
    t.claim("Grace", "full_house")
    t.broadcaster.sent.clear()

    t.scheduler.close_all()

    assert [e[0] for e in t.broadcaster.sent] == [
        "claim_logged",
        "claim_logged",
        "prize_awarded",
        "game_ended",
        "claim_settled",
        "claim_settled",
        "window_changed",
    ]
    assert ("game_ended", t.game.code, {"reason": "full_house"}) in t.broadcaster.sent


def test_ending_the_game_mid_window_refuses_the_claimants_at_once_and_the_late_close_sends_nothing():
    t = Table()
    t.claim("Ada")
    t.claim("Grace")
    t.broadcaster.sent.clear()

    ended = run(t.adapter.end_game("sid-host", host_message(t.game)))
    sent_by_end = list(t.broadcaster.sent)
    t.scheduler.close_all()

    assert ended == {"ok": True}
    assert sent_by_end == [
        logged(t, "Ada", False, "game_ended"),
        logged(t, "Grace", False, "game_ended"),
        ("game_ended", t.game.code, {"reason": "host"}),
        settled(t, "Ada", False, "game_ended"),
        settled(t, "Grace", False, "game_ended"),
        window(t, False),
    ]
    assert t.broadcaster.sent == sent_by_end


def test_a_failed_send_is_logged_and_every_other_send_still_goes_out(caplog):
    t = Table()
    t.claim("Ada")
    t.claim("Grace")
    t.broadcaster.sent.clear()
    t.broadcaster.failing = {"prize_awarded", "claim_logged"}

    with caplog.at_level(logging.ERROR, logger="devbingo_backend.realtime"):
        t.scheduler.close_all()

    assert t.broadcaster.sent == [settled(t, "Ada"), settled(t, "Grace"), window(t, False)]
    assert len(caplog.records) == 3
    assert all(record.exc_info for record in caplog.records)
    assert t.registry.prize_board(t.game.code)[Prize.EARLY_FIVE] == ["Ada", "Grace"]


def test_on_the_real_clock_a_claim_is_waiting_then_settled_without_being_asked_again():
    # Nothing is scheduled until the claim, so the table is set up before the loop that runs it.
    t = Table(scheduler=AsyncioScheduler())

    async def scenario():
        ack = await t.adapter.claim_prize("sid-ada", {"prize": "early_five"})
        for _ in range(5):
            await asyncio.sleep(0)
        return ack

    assert asyncio.run(scenario()) == {"ok": True, "waiting": True}
    assert settled(t, "Ada") in t.broadcaster.sent
