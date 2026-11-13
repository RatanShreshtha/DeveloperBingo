"""The engine closes its own settlement windows: each one closes once, after the window length, and
its outcome goes to the listener. No sockets are involved."""

import asyncio
import random

import pytest
from helpers import ManualScheduler, draw_everything, names_on

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import (
    DEFAULT_WINDOW_SECONDS,
    GameRegistry,
    Outcome,
    PlayerRef,
)
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord


class Table:
    """Ada and Grace have joined, every topic is drawn and each has ticked five. Every outcome
    a window reports on closing is kept in `heard`."""

    def __init__(self, window_seconds: float = DEFAULT_WINDOW_SECONDS) -> None:
        self.scheduler = ManualScheduler()
        self.registry = GameRegistry(
            rng=random.Random(7),
            scheduler=self.scheduler,
            window_seconds=window_seconds,
        )
        self.heard: list[tuple[str, Outcome]] = []

        async def listen(code: str, outcome: Outcome) -> None:
            self.heard.append((code, outcome))

        self.registry.listen(listen)
        self.game = self.registry.create_game(DEFAULT_POOL)
        self.tickets = {
            name: self.registry.join(self.player(name)).snapshot.ticket
            for name in ("Ada", "Grace")
        }
        self.registry.start(self.game)
        draw_everything(self.registry, self.game)
        for name, ticket in self.tickets.items():
            for topic in names_on(ticket)[:5]:
                self.registry.tick(self.player(name), topic)

    def player(self, name: str) -> PlayerRef:
        return PlayerRef(self.game.code, name)

    def tick_everything(self, name: str) -> None:
        for topic in names_on(self.tickets[name]):
            self.registry.tick(self.player(name), topic)


@pytest.fixture
def table() -> Table:
    return Table()


def test_a_window_is_scheduled_once_with_the_window_length():
    t = Table(window_seconds=2.5)

    t.registry.claim(t.player("Ada"), Prize.EARLY_FIVE)
    t.registry.claim(t.player("Grace"), Prize.EARLY_FIVE)
    t.registry.claim(t.player("Ada"), Prize.EARLY_FIVE)

    assert t.scheduler.delays == [2.5]


def test_the_window_length_defaults_to_one_second():
    assert DEFAULT_WINDOW_SECONDS == 1.0


def test_a_window_closing_on_time_tells_the_listener_who_won_and_that_no_window_is_open(
    table,
):
    table.registry.claim(table.player("Ada"), Prize.EARLY_FIVE)
    table.registry.claim(table.player("Grace"), Prize.EARLY_FIVE)

    table.scheduler.close_all()

    [(code, outcome)] = table.heard
    assert code == table.game.code
    (settled,) = outcome.settled
    assert settled.awarded_to == ("Ada", "Grace")
    assert settled.records == (
        ClaimRecord("Ada", Prize.EARLY_FIVE, accepted=True),
        ClaimRecord("Grace", Prize.EARLY_FIVE, accepted=True),
    )
    assert outcome.ended is None
    assert outcome.window_open is False
    assert table.registry.host_snapshot(table.game).prizes[Prize.EARLY_FIVE] == (
        "Ada",
        "Grace",
    )


def test_nothing_is_heard_or_awarded_before_the_window_closes(table):
    table.registry.claim(table.player("Ada"), Prize.EARLY_FIVE)

    assert table.heard == []
    assert table.registry.host_snapshot(table.game).prizes[Prize.EARLY_FIVE] == ()


def test_the_close_scheduled_before_the_host_ended_the_game_changes_nothing(table):
    table.registry.claim(table.player("Ada"), Prize.EARLY_FIVE)
    table.registry.end(table.game)
    log_before = table.registry.host_snapshot(table.game).claims

    table.scheduler.close_all()

    assert table.heard == []
    assert table.registry.host_snapshot(table.game).claims == log_before
    assert all(
        names == ()
        for names in table.registry.host_snapshot(table.game).prizes.values()
    )


def test_windows_for_two_prizes_open_together_and_close_independently(table):
    table.tick_everything("Ada")

    first = table.registry.claim(table.player("Ada"), Prize.EARLY_FIVE)
    second = table.registry.claim(table.player("Ada"), Prize.TOP_LINE)
    close_early_five, close_top_line = table.scheduler.pending

    asyncio.run(close_early_five())
    asyncio.run(close_top_line())

    # Only the first claim opened the game's first window; the second opened another beside it.
    assert (first.outcome.window_open, second.outcome.window_open) == (True, None)
    [(_, five), (_, top)] = table.heard
    assert (five.settled[0].prize, five.window_open) == (Prize.EARLY_FIVE, None)
    assert (top.settled[0].prize, top.window_open) == (Prize.TOP_LINE, False)


def test_a_window_still_closes_with_no_listener():
    registry = GameRegistry(
        rng=random.Random(7), scheduler=(scheduler := ManualScheduler())
    )
    game = registry.create_game(DEFAULT_POOL)
    ada = PlayerRef(game.code, "Ada")
    ticket = registry.join(ada).snapshot.ticket
    registry.start(game)
    draw_everything(registry, game)
    for topic in names_on(ticket)[:5]:
        registry.tick(ada, topic)
    registry.claim(ada, Prize.EARLY_FIVE)

    scheduler.close_all()

    assert registry.host_snapshot(game).prizes[Prize.EARLY_FIVE] == ("Ada",)
