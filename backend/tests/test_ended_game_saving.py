"""The socket adapter keeps an ended game's summary on a worker thread, after the room hears the end.
A keeper that fails never stops the game, and a keeper that is slow never holds up other commands."""

import asyncio
import logging
import threading

from helpers import RealtimeTable, host_message, run

from devbingo_backend.errors import ErrorCode


def test_the_keeper_receives_the_summary_of_an_ended_game_off_the_event_loop():
    kept: list[tuple[str, int]] = []

    def keep(summary):
        kept.append((summary.end_reason, threading.get_ident()))

    table = RealtimeTable(on_ended=keep)
    ack = run(table.adapter.end_game("sid-host", host_message(table.game)))

    assert ack == {"ok": True}
    ((end_reason, thread),) = kept
    assert end_reason == "host"
    assert thread != threading.get_ident()


def test_a_failing_keeper_does_not_stop_the_game_ending(caplog):
    def boom(_summary):
        raise RuntimeError("store down")

    table = RealtimeTable(on_ended=boom)
    with caplog.at_level(logging.ERROR):
        ack = run(table.adapter.end_game("sid-host", host_message(table.game)))

    assert ack == {"ok": True}
    assert any(r.exc_info for r in caplog.records)
    refusal = run(table.adapter.start_game("sid-host", host_message(table.game)))
    assert refusal["error"] == ErrorCode.GAME_ENDED


def test_a_slow_keeper_does_not_hold_up_other_commands_while_it_saves():
    saving = threading.Event()
    release = threading.Event()

    def slow_keeper(_summary):
        saving.set()
        release.wait(timeout=5)

    table = RealtimeTable(on_ended=slow_keeper)

    async def scenario():
        end = asyncio.create_task(
            table.adapter.end_game("sid-host", host_message(table.game))
        )
        # Wait until the keeper is running on its worker thread.
        await asyncio.to_thread(saving.wait, 5)
        # Another command is served while the save is still in progress.
        watch = await table.adapter.watch_lobby("sid-host", host_message(table.game))
        still_saving = not end.done()
        release.set()
        await end
        return still_saving, watch

    still_saving, watch = run(scenario())

    assert still_saving
    assert "error" not in watch
