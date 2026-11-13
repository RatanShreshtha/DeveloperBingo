"""Setup shared by the engine tests and the realtime tests."""

import asyncio
import random

from devbingo_backend.default_pool import DEFAULT_POOL
from devbingo_backend.game import GameRegistry, HostLink, Outcome, PlayerRef
from devbingo_backend.pool import Topic
from devbingo_backend.prizes import Prize
from devbingo_backend.realtime import RealtimeAdapter
from devbingo_backend.ticket import Ticket


def ticket_of(grid: list[list[str | None]]) -> Ticket:
    """A ticket laid out exactly as given, so a test can control which cells are filled."""
    return Ticket(
        tuple(
            tuple(Topic(name, f"{name} explained") if name else None for name in line)
            for line in grid
        )
    )


def names_on(ticket: Ticket) -> list[str]:
    """The topic names on a ticket, in a fixed order.

    Read straight from the lines, deliberately not through the ticket's own
    `topic_names()`, so tests check the engine against the ticket's contents.
    """
    return sorted({cell.name for line in ticket.lines for cell in line if cell is not None})


def draw_everything(registry: GameRegistry, game: HostLink) -> None:
    """Draw every topic in the pool, so any topic may be ticked. The game must have started."""
    for _ in range(len(DEFAULT_POOL.topics)):
        registry.draw(game)


def start_and_draw_everything(registry: GameRegistry, game: HostLink) -> None:
    registry.start(game)
    draw_everything(registry, game)


def board_of(**awarded_to: list[str]) -> dict[Prize, list[str]]:
    """The prize board with every prize open, except those given as `prize_name=[names]`."""
    return {prize: awarded_to.get(prize.value, []) for prize in Prize}


def wire_board_of(**awarded_to: list[str]) -> list[dict]:
    """The prize board as the wire carries it: every prize in order, with who holds it."""
    return [{"prize": prize.value, "awarded_to": awarded_to.get(prize.value, [])} for prize in Prize]


def claim_and_settle(registry: "ManualRegistry", player: PlayerRef, prize: Prize) -> Outcome:
    """Claim a prize and let its settlement window close, as if no one else claimed in it.
    Returns what the close reported."""
    registry.claim(player, prize)
    (outcome,) = registry.settle()
    return outcome


class ManualScheduler:
    """Keeps the settlement window closes the registry schedules until the test fires them, so no
    test waits on a clock."""

    def __init__(self) -> None:
        self.pending: list = []
        self.delays: list[float] = []

    def call_later(self, delay, action) -> None:
        self.delays.append(delay)
        self.pending.append(action)

    async def fire_all(self) -> None:
        pending, self.pending = self.pending, []
        for action in pending:
            await action()

    def close_all(self) -> None:
        """Fire every pending close, outside an event loop."""
        asyncio.run(self.fire_all())



class ManualRegistry(GameRegistry):
    """A registry whose settlement windows close when the test says so, by firing the closes its
    scheduler holds: the same path the clock runs in production."""

    def __init__(self, **kwargs) -> None:
        self.scheduler = ManualScheduler()
        super().__init__(scheduler=self.scheduler, **kwargs)

    def settle(self) -> list[Outcome]:
        """Fire every pending close. Returns what each reported, in the order they fired; a close
        with nothing to settle reports nothing. Whoever was listening still hears each one."""
        heard: list[Outcome] = []
        listener = self._on_outcome

        async def hear(code: str, outcome: Outcome) -> None:
            heard.append(outcome)
            if listener is not None:
                await listener(code, outcome)

        self.listen(hear)
        try:
            self.scheduler.close_all()
        finally:
            self._on_outcome = listener
        return heard


def run(coro):
    return asyncio.run(coro)


def topics_on(cells):
    """The topic names in a ticket as the wire carries it."""
    return sorted({cell for line in cells for cell in line if cell})


def host_message(game):
    return {"code": game.code, "host_token": game.host_token}


def tick_message(game, topic, name="Ada"):
    return {"code": game.code, "name": name, "topic": topic}


def claim_message(game, name="Ada", prize="early_five"):
    return {"code": game.code, "name": name, "prize": prize}


class RecordingBroadcaster:
    """Stands in for the Socket.IO server. Records every message in the order sent, and raises for
    the events in `failing`. `emitted` is what was announced and `window_changes` is the host's
    window hint, kept apart so assertions about announcements need not mention it."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, object]] = []
        self.entered: list[tuple[str, str]] = []
        self.left: list[tuple[str, str]] = []
        self.failing: set[str] = set()

    @property
    def emitted(self) -> list[tuple[str, str, object]]:
        return [message for message in self.sent if message[0] != "window_changed"]

    @property
    def window_changes(self) -> list[tuple[str, str, object]]:
        return [message for message in self.sent if message[0] == "window_changed"]

    async def enter_room(self, sid: str, room: str) -> None:
        self.entered.append((sid, room))

    async def leave_room(self, sid: str, room: str) -> None:
        self.left.append((sid, room))

    async def emit(self, event, data, room=None, to=None) -> None:
        if event in self.failing:
            raise RuntimeError(f"cannot emit {event}")
        self.sent.append((event, room or to or "", data))


class RealtimeTable:
    """A game played through the realtime adapter: the registry, the adapter, a broadcaster that
    records every message and a scheduler that closes windows only when the test says so. Players
    are on sockets named "sid-<name>" unless a test says otherwise."""

    def __init__(self, seed: int = 5, scheduler=None, window_seconds: float | None = None) -> None:
        self.scheduler = scheduler or ManualScheduler()
        options = {} if window_seconds is None else {"window_seconds": window_seconds}
        self.registry = GameRegistry(rng=random.Random(seed), scheduler=self.scheduler, **options)
        self.game = self.registry.create_game(DEFAULT_POOL, pool_name="Default")
        self.broadcaster = RecordingBroadcaster()
        self.adapter = RealtimeAdapter(self.registry, self.broadcaster)
        self.tickets: dict[str, list] = {}

    @staticmethod
    def sid(name: str) -> str:
        return f"sid-{name.strip().lower()}"

    @property
    def host(self) -> str:
        """The room only the host is in."""
        return f"{self.game.code}:host"

    def join(self, sid: str = "sid-ada", name: str = "Ada", **extra) -> dict:
        ack = run(self.adapter.join_game(sid, {"code": self.game.code, "name": name, **extra}))
        if ack.get("ok"):
            self.tickets[name] = ack["ticket"]
        return ack

    def join_players(self, *names: str) -> None:
        for name in names:
            self.join(self.sid(name), name)

    def watch(self, sid: str = "sid-host") -> dict:
        return run(self.adapter.watch_lobby(sid, host_message(self.game)))

    def start_and_draw_everything(self) -> None:
        start_and_draw_everything(self.registry, self.game)

    def tick(self, name: str = "Ada", topics=None) -> None:
        """The player ticks these topics, or the first five on their ticket when none are named."""
        for topic in topics if topics is not None else topics_on(self.tickets[name])[:5]:
            run(self.adapter.tick_topic(self.sid(name), tick_message(self.game, topic, name)))

    def ready_to_claim(self, name: str = "Ada", whole_ticket: bool = False) -> dict:
        """The player has joined, the game has started, every topic is drawn and they have ticked
        five topics, or their whole ticket. Returns the player's join acknowledgement."""
        ack = self.join(self.sid(name), name)
        self.start_and_draw_everything()
        self.tick(name, topics_on(ack["ticket"]) if whole_ticket else None)
        return ack

    def claim(self, name: str = "Ada", prize: str = "early_five") -> dict:
        return run(self.adapter.claim_prize(self.sid(name), {"prize": prize}))

    def settle(self) -> None:
        """Every settlement window that is open closes now."""
        self.scheduler.close_all()

    def claim_and_close(self, name: str = "Ada", prize: str = "early_five") -> dict:
        ack = self.claim(name, prize)
        self.settle()
        return ack

    def disconnect(self, sid: str) -> None:
        run(self.adapter.disconnect(sid))

    def to_room(self) -> list[tuple[str, str, object]]:
        """What was announced to the game's room, where every player is. The host's room is left out."""
        return [message for message in self.broadcaster.emitted if message[1] == self.game.code]

    def settled_for(self, sid: str = "sid-ada") -> list[object]:
        return [
            data
            for event, target, data in self.broadcaster.emitted
            if event == "claim_settled" and target == sid
        ]
