import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol


class Scheduler(Protocol):
    """Runs an action after a delay. The engine closes each settlement window through this, and
    tests fake it to close windows without waiting."""

    def call_later(
        self, delay: float, action: Callable[[], Awaitable[None]]
    ) -> None: ...


class AsyncioScheduler:
    def __init__(self) -> None:
        # Held so a task is not garbage-collected before it runs.
        self._tasks: set[asyncio.Task[None]] = set()

    def call_later(self, delay: float, action: Callable[[], Awaitable[None]]) -> None:
        async def run() -> None:
            await asyncio.sleep(delay)
            await action()

        task = asyncio.get_running_loop().create_task(run())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
