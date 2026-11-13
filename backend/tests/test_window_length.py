"""The settlement window's length reaches the game registry, and the real scheduler runs what it is given."""

import asyncio

import pytest

from devbingo_backend import app as app_module
from devbingo_backend.app import create_app
from devbingo_backend.game import GameRegistry
from devbingo_backend.pool_library import InMemoryPoolLibrary
from devbingo_backend.scheduler import AsyncioScheduler


@pytest.fixture
def window_given_to_the_registry(monkeypatch):
    seen: list[float] = []

    def spy(**options):
        seen.append(options["window_seconds"])
        return GameRegistry(**options)

    monkeypatch.setattr(app_module, "GameRegistry", spy)
    return seen


def test_the_window_length_can_be_passed_to_create_app(
    window_given_to_the_registry, monkeypatch
):
    monkeypatch.setenv("SETTLEMENT_WINDOW_SECONDS", "9")

    create_app(pool_library=InMemoryPoolLibrary(), settlement_window_seconds=0.25)

    assert window_given_to_the_registry == [0.25]


def test_the_window_length_comes_from_the_environment(
    window_given_to_the_registry, monkeypatch
):
    monkeypatch.setenv("SETTLEMENT_WINDOW_SECONDS", "2.5")

    create_app(pool_library=InMemoryPoolLibrary())

    assert window_given_to_the_registry == [2.5]


def test_the_window_length_defaults_to_one_second(
    window_given_to_the_registry, monkeypatch
):
    monkeypatch.delenv("SETTLEMENT_WINDOW_SECONDS", raising=False)

    create_app(pool_library=InMemoryPoolLibrary())

    assert window_given_to_the_registry == [1.0]


def test_the_asyncio_scheduler_runs_the_action_after_the_delay():
    ran: list[str] = []

    async def scenario():
        scheduler = AsyncioScheduler()

        async def action():
            ran.append("closed")

        scheduler.call_later(0.01, action)
        await asyncio.sleep(0)
        before = list(ran)
        await asyncio.sleep(0.05)
        return before, scheduler

    before, scheduler = asyncio.run(scenario())

    assert before == []
    assert ran == ["closed"]
    assert scheduler._tasks == set()
