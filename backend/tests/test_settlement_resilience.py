"""Windows always close, the host can end the game mid-window, and windows for different prizes are
independent."""

import asyncio
import logging

from devbingo_backend.prizes import Prize
from test_realtime import RecordingBroadcaster, host_message, tick_message, topics_on
from test_settlement_realtime import (
    ADA_AND_GRACE,
    claim_task,
    claims_then_close,
    emitted,
    settle_soon,
    table,
)


class FailingBroadcaster(RecordingBroadcaster):
    """Records like the real thing, but raises when asked to emit the events in `failing`."""

    def __init__(self) -> None:
        super().__init__()
        self.failing: set[str] = set()

    async def emit(self, event, data, room=None, to=None) -> None:
        if event in self.failing:
            raise RuntimeError(f"cannot emit {event}")
        await super().emit(event, data, room=room, to=to)


def failing_table():
    return table(broadcaster=FailingBroadcaster())


def test_every_held_acknowledgement_is_answered_when_announcing_the_winners_fails(caplog):
    t = failing_table()
    t.broadcaster.failing = {"prize_awarded"}

    with caplog.at_level(logging.ERROR, logger="devbingo_backend.realtime"):
        _, acks = claims_then_close(t, ADA_AND_GRACE)

    assert acks == [{"ok": True}, {"ok": True}]
    assert [r.name for r in caplog.records] == ["devbingo_backend.realtime"]
    assert caplog.records[0].exc_info is not None


def test_every_held_acknowledgement_is_answered_when_telling_the_host_fails(caplog):
    t = failing_table()
    t.broadcaster.failing = {"claim_logged"}

    with caplog.at_level(logging.ERROR, logger="devbingo_backend.realtime"):
        _, acks = claims_then_close(t, ADA_AND_GRACE)

    assert acks == [{"ok": True}, {"ok": True}]
    assert len(caplog.records) == 1


def test_the_draw_hold_is_gone_after_a_close_whose_announcement_failed():
    t = failing_table()
    t.broadcaster.failing = {"prize_awarded", "claim_logged"}
    claims_then_close(t, ADA_AND_GRACE)

    after = asyncio.run(t.adapter.draw_topic("sid-host", host_message(t.game)))

    # Every topic is already drawn, so the pool refuses: the settlement hold is not what refuses.
    assert after == {"ok": False, "error": "no_topics_left"}


def test_the_winners_are_awarded_even_when_the_announcement_failed():
    t = failing_table()
    t.broadcaster.failing = {"prize_awarded"}
    claims_then_close(t, ADA_AND_GRACE)

    assert t.registry.prize_board(t.game.code)[Prize.EARLY_FIVE] == ["Ada", "Grace"]


def test_ending_the_game_mid_window_answers_the_claimants_at_once_without_the_window_closing():
    t = table()

    async def scenario():
        tasks = [claim_task(t, sid, name) for sid, name in ADA_AND_GRACE]
        await settle_soon()
        ended = await t.adapter.end_game("sid-host", host_message(t.game))
        await settle_soon()
        return ended, [task.done() for task in tasks], [await task for task in tasks]

    ended, done_before_close, acks = asyncio.run(scenario())

    assert ended == {"ok": True}
    assert done_before_close == [True, True]
    assert acks == [{"ok": False, "error": "game_ended"}] * 2


def test_the_host_log_records_the_refusals_before_the_game_ended_announcement():
    t = table()

    async def scenario():
        await t.adapter.watch_lobby("sid-host", host_message(t.game))
        tasks = [claim_task(t, sid, name) for sid, name in ADA_AND_GRACE]
        await settle_soon()
        await t.adapter.end_game("sid-host", host_message(t.game))
        await asyncio.gather(*tasks)

    asyncio.run(scenario())

    refused = lambda who: (  # noqa: E731
        "claim_logged",
        f"{t.game.code}:host",
        {"player": who, "prize": "early_five", "accepted": False, "error": "game_ended"},
    )
    assert emitted(t, "claim_logged", "game_ended", "prize_awarded") == [
        refused("Ada"),
        refused("Grace"),
        ("game_ended", t.game.code, {"reason": "host"}),
    ]


def test_the_close_scheduled_before_the_host_ended_the_game_changes_nothing():
    t = table()

    async def scenario():
        tasks = [claim_task(t, sid, name) for sid, name in ADA_AND_GRACE]
        await settle_soon()
        await t.adapter.end_game("sid-host", host_message(t.game))
        await asyncio.gather(*tasks)
        before = list(t.broadcaster.emitted)
        await t.scheduler.fire_all()
        return before

    before = asyncio.run(scenario())

    assert t.broadcaster.emitted == before
    assert all(names == [] for names in t.registry.prize_board(t.game.code).values())


def test_windows_for_two_prizes_are_open_together_and_settle_independently():
    t = table()

    async def scenario():
        for topic in topics_on(t.tickets["Ada"]):
            await t.adapter.tick_topic("sid-ada", tick_message(t.game, topic))
        five = claim_task(t, "sid-ada", "Ada", "early_five")
        await settle_soon()
        top = claim_task(t, "sid-ada", "Ada", "top_line")
        await settle_soon()
        opened = len(t.scheduler.scheduled)
        # Only the first window's close fires: the second prize stays open and its claim is held.
        first = t.scheduler.scheduled.pop(0)
        await first()
        await settle_soon()
        after_first = (five.done(), top.done(), emitted(t, "prize_awarded"))
        await t.scheduler.fire_all()
        return opened, after_first, await five, await top

    opened, after_first, five_ack, top_ack = asyncio.run(scenario())

    assert opened == 2
    assert after_first == (
        True,
        False,
        [("prize_awarded", t.game.code, {"prize": "early_five", "awarded_to": ["Ada"]})],
    )
    assert (five_ack, top_ack) == ({"ok": True}, {"ok": True})
    assert emitted(t, "prize_awarded")[1] == (
        "prize_awarded",
        t.game.code,
        {"prize": "top_line", "awarded_to": ["Ada"]},
    )
