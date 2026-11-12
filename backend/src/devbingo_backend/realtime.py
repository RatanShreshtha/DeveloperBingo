import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, Literal, Protocol, TypeVar

import socketio
from pydantic import BaseModel, ValidationError

from devbingo_backend.game import (
    AlreadyJoined,
    GameError,
    GameRegistry,
    InvalidMessage,
    NotJoined,
    PlayerRef,
    UnknownPrize,
)
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord, Settled
from devbingo_backend.wire import (
    Accepted,
    ClaimLogEntry,
    ClaimPayload,
    ClientEvent,
    DrawAck,
    DrawAnnouncement,
    GameEnded,
    GameStarted,
    HostLink,
    JoinAck,
    JoinPayload,
    LobbyUpdated,
    PrizeAwarded,
    PoolResponse,
    PrizeBoardEntry,
    Refusal,
    Replaced,
    ServerEvent,
    TickPayload,
    WatchAck,
    WindowChanged,
)


class Broadcaster(Protocol):
    """The part of the Socket.IO server the adapter needs, so tests can fake it."""

    async def enter_room(self, sid: str, room: str) -> None: ...

    async def leave_room(self, sid: str, room: str) -> None: ...

    async def emit(
        self,
        event: str,
        data: Any,
        room: str | None = None,
        to: str | None = None,
    ) -> None: ...


class Scheduler(Protocol):
    """Runs an action after a delay. The engine has no clock, so the adapter asks for the close of
    each settlement window here, and tests fake it to close windows without waiting."""

    def call_later(self, delay: float, action: Callable[[], Awaitable[None]]) -> None: ...


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


logger = logging.getLogger(__name__)

# How long a settlement window stays open, unless the app is configured otherwise.
DEFAULT_WINDOW_SECONDS = 1.0

Ack = dict[str, Any]
M = TypeVar("M", bound=BaseModel)


def _refusal(err: GameError) -> Ack:
    """The acknowledgement that tells only the sender why a request was refused."""
    return Refusal(error=err.code).model_dump(mode="json")


def _parse(model: type[M], payload: object) -> M:
    """Reads a payload into its model. A bad or missing field refuses the whole message."""
    try:
        return model.model_validate(payload)
    except ValidationError:
        raise InvalidMessage from None


def _prize_board(board: dict[Prize, list[str]]) -> list[PrizeBoardEntry]:
    """The prize board in the order the engine keeps it."""
    return [PrizeBoardEntry(prize=prize, awarded_to=names) for prize, names in board.items()]


def _claim_entry(record: ClaimRecord) -> ClaimLogEntry:
    return ClaimLogEntry(
        player=record.player, prize=record.prize, accepted=record.accepted, error=record.error
    )


def _host_room(code: str) -> str:
    """The room only the game's host sockets are in. The game's own room has every player too."""
    return f"{code}:host"


class RealtimeAdapter:
    """Turns socket events into engine calls and engine state into room broadcasts.

    Holds no game rules: the registry decides, the adapter only reports.
    """

    def __init__(
        self,
        registry: GameRegistry,
        broadcaster: Broadcaster,
        scheduler: Scheduler | None = None,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self._registry = registry
        self._broadcaster = broadcaster
        self._scheduler = scheduler or AsyncioScheduler()
        self._window_seconds = window_seconds
        # The claimants' acknowledgements held open, by the window they wait on.
        self._held: dict[tuple[str, Prize], list[tuple[str, asyncio.Future[Ack]]]] = {}
        # Which player each live socket belongs to, so a dropped socket frees its name.
        self._sessions: dict[str, PlayerRef] = {}

    def _player_on(self, sid: str) -> PlayerRef:
        """Whoever joined on this socket. A command never names its own player."""
        player = self._sessions.get(sid)
        if player is None:
            raise NotJoined
        return player

    async def join_game(self, sid: str, payload: object) -> Ack:
        try:
            message = _parse(JoinPayload, payload)
            # One socket is one player. Joining again on the same socket would leave the
            # first player connected for ever, so it is refused.
            if sid in self._sessions:
                raise AlreadyJoined
            joined = self._registry.join(
                PlayerRef(code=message.code, name=message.name), message.rejoin_token
            )
        except GameError as err:
            return _refusal(err)

        # From here on the player is the one the game knows, not the name as this client typed it.
        player = joined.player

        if joined.took_over:
            await self._replace_sockets_of(player, keep=sid)
        self._sessions[sid] = player
        await self._broadcaster.enter_room(sid, player.code)
        # Only a new player changes the lobby. A rejoin changes nothing for the others.
        if joined.is_new_player:
            await self._broadcaster.emit(
                ServerEvent.LOBBY_UPDATED,
                LobbyUpdated(players=self._registry.players(player.code)).model_dump(mode="json"),
                room=player.code,
            )
        # A rejoin restores the ticks the player already had, so they come back here.
        return JoinAck(
            **self._snapshot(player.code),
            name=player.name,
            ticket=joined.ticket.to_cells(),
            ticks=sorted(self._registry.ticks(player)),
            pending_claims=self._registry.pending_claims(player),
            rejoin_token=joined.rejoin_token,
        ).model_dump(mode="json")

    def _snapshot(self, code: str) -> dict[str, Any]:
        """The parts of a snapshot that every client gets."""
        return {
            "status": self._registry.status(code),
            "end_reason": self._registry.end_reason(code),
            "players": self._registry.players(code),
            "draws": [DrawAnnouncement.from_draw(draw) for draw in self._registry.draw_history(code)],
            "prizes": _prize_board(self._registry.prize_board(code)),
        }

    async def _replace_sockets_of(self, player: PlayerRef, keep: str) -> None:
        """Tells every other socket holding this player that it was replaced, and takes it out of the game."""
        for old, held in list(self._sessions.items()):
            if old != keep and held == player:
                del self._sessions[old]
                await self._broadcaster.leave_room(old, player.code)
                await self._broadcaster.emit(
                    ServerEvent.REPLACED, Replaced().model_dump(mode="json"), to=old
                )

    async def disconnect(self, sid: str) -> None:
        """A socket has dropped. The player keeps their place and can rejoin by name."""
        player = self._sessions.pop(sid, None)
        if player is not None:
            self._registry.disconnect(player)

    async def watch_lobby(self, sid: str, payload: object) -> Ack:
        try:
            host = _parse(HostLink, payload)
            self._registry.lobby(host)
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.enter_room(sid, host.code)
        await self._broadcaster.enter_room(sid, _host_room(host.code))
        return WatchAck(
            **self._snapshot(host.code),
            claims=[_claim_entry(record) for record in self._registry.claim_log(host.code)],
            pool=PoolResponse.from_pool(self._registry.pool_of(host.code)),
            pool_name=self._registry.pool_name_of(host.code),
            window_open=self._registry.window_open(host.code),
        ).model_dump(mode="json")

    async def start_game(self, sid: str, payload: object) -> Ack:
        try:
            host = _parse(HostLink, payload)
            self._registry.start(host)
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.emit(
            ServerEvent.GAME_STARTED, GameStarted().model_dump(mode="json"), room=host.code
        )
        return Accepted().model_dump(mode="json")

    async def draw_topic(self, sid: str, payload: object) -> Ack:
        try:
            host = _parse(HostLink, payload)
            draw = self._registry.draw(host)
        except GameError as err:
            return _refusal(err)

        announcement = DrawAnnouncement.from_draw(draw)
        await self._broadcaster.emit(
            ServerEvent.TOPIC_DRAWN, announcement.model_dump(mode="json"), room=host.code
        )
        return DrawAck(draw=announcement).model_dump(mode="json")

    async def _announce_end(self, code: str, reason: Literal["full_house", "host"]) -> None:
        await self._broadcaster.emit(
            ServerEvent.GAME_ENDED, GameEnded(reason=reason).model_dump(mode="json"), room=code
        )

    async def end_game(self, sid: str, payload: object) -> Ack:
        """The host ends the game. Windows still open settle at once, refused; everyone in the room is told."""
        try:
            host = _parse(HostLink, payload)
            settled = self._registry.end(host)
        except GameError as err:
            return _refusal(err)

        await self._announce(
            host.code,
            settled,
            lambda: self._announce_end(host.code, "host"),
        )
        await self._tell_window(host.code)
        return Accepted().model_dump(mode="json")

    async def claim_prize(self, sid: str, payload: object) -> Ack:
        """A refused claim is told to the claimant at once. A valid one waits in the prize's settlement
        window: the acknowledgement is held until the window settles, then says awarded or refused."""
        try:
            message = _parse(ClaimPayload, payload)
            player = self._player_on(sid)
            try:
                prize = Prize(message.prize)
            except ValueError:
                raise UnknownPrize from None
            try:
                pending = self._registry.claim(player, prize)
            except GameError as err:
                if err.record is not None:
                    await self._tell_host(player.code, err.record)
                raise
        except GameError as err:
            return _refusal(err)

        answer: asyncio.Future[Ack] = asyncio.get_running_loop().create_future()
        self._held.setdefault((player.code, prize), []).append((player.name, answer))
        if pending.opened_window:
            await self._tell_window(player.code)
            self._scheduler.call_later(
                self._window_seconds, lambda: self.close_window(player.code, prize)
            )
        return await answer

    async def close_window(self, code: str, prize: Prize) -> None:
        """Close the prize's settlement window. Tells the host of each claim, the room of the winners
        (once) and of the game's end, and answers every held acknowledgement, even if telling fails."""
        settled = self._registry.close_window(code, prize)
        if settled is None:
            return

        async def announce_room() -> None:
            if settled.awarded_to:
                await self._broadcaster.emit(
                    ServerEvent.PRIZE_AWARDED,
                    PrizeAwarded(prize=prize, awarded_to=list(settled.awarded_to)).model_dump(mode="json"),
                    room=code,
                )
            if settled.ends_game:
                await self._announce_end(code, "full_house")

        await self._announce(code, [settled], announce_room)
        await self._tell_window(code)

    async def _announce(
        self,
        code: str,
        settled: Iterable[Settled],
        announce_room: Callable[[], Awaitable[None]],
    ) -> None:
        """Tells the host of each settled claim, then the room, and answers the held acknowledgements.
        The answers go out whatever happens to the announcements, which only get logged if they fail."""
        settled = list(settled)
        try:
            for outcome in settled:
                for record in outcome.records:
                    await self._tell_host(code, record)
            await announce_room()
        except Exception:
            logger.exception("could not announce the settlement in game %s", code)
        finally:
            for outcome in settled:
                self._answer_held(code, outcome)

    def _answer_held(self, code: str, settled: Settled) -> None:
        decided = {record.player: record for record in settled.records}
        for name, answer in self._held.pop((code, settled.prize), []):
            record = decided[name]
            if record.accepted:
                result = Accepted().model_dump(mode="json")
            else:
                assert record.error is not None
                result = Refusal(error=record.error).model_dump(mode="json")
            if not answer.done():
                answer.set_result(result)

    async def _tell_window(self, code: str) -> None:
        """Tells the host whether a settlement window is open now. A failure is only logged."""
        try:
            await self._broadcaster.emit(
                ServerEvent.WINDOW_CHANGED,
                WindowChanged(open=self._registry.window_open(code)).model_dump(mode="json"),
                room=_host_room(code),
            )
        except Exception:
            logger.exception("could not tell the host about the settlement window in game %s", code)

    async def _tell_host(self, code: str, record: ClaimRecord) -> None:
        """Sends the host one decided claim, and nobody else."""
        await self._broadcaster.emit(
            ServerEvent.CLAIM_LOGGED,
            _claim_entry(record).model_dump(mode="json"),
            room=_host_room(code),
        )

    # Ticks are private, and nothing is broadcast. The acknowledgement says only
    # whether the change happened: the client keeps its own list, so no ticks are
    # sent back to anyone.

    async def tick_topic(self, sid: str, payload: object) -> Ack:
        return self._change_ticks(sid, payload, self._registry.tick)

    async def untick_topic(self, sid: str, payload: object) -> Ack:
        return self._change_ticks(sid, payload, self._registry.untick)

    def _change_ticks(
        self, sid: str, payload: object, change: Callable[[PlayerRef, str], None]
    ) -> Ack:
        try:
            message = _parse(TickPayload, payload)
            change(self._player_on(sid), message.topic)
        except GameError as err:
            return _refusal(err)
        return Accepted().model_dump(mode="json")


class _SocketIOBroadcaster:
    def __init__(self, server: socketio.AsyncServer) -> None:
        self._server = server

    async def enter_room(self, sid: str, room: str) -> None:
        await self._server.enter_room(sid, room)

    async def leave_room(self, sid: str, room: str) -> None:
        await self._server.leave_room(sid, room)

    async def emit(
        self,
        event: str,
        data: Any,
        room: str | None = None,
        to: str | None = None,
    ) -> None:
        await self._server.emit(event, data, room=room, to=to)


def build_socket_server(
    registry: GameRegistry, window_seconds: float = DEFAULT_WINDOW_SECONDS
) -> socketio.AsyncServer:
    server = socketio.AsyncServer(async_mode="asgi")
    adapter = RealtimeAdapter(registry, _SocketIOBroadcaster(server), window_seconds=window_seconds)

    commands: dict[ClientEvent, Callable[[str, Any], Awaitable[Ack]]] = {
        ClientEvent.JOIN_GAME: adapter.join_game,
        ClientEvent.WATCH_LOBBY: adapter.watch_lobby,
        ClientEvent.START_GAME: adapter.start_game,
        ClientEvent.DRAW_TOPIC: adapter.draw_topic,
        ClientEvent.END_GAME: adapter.end_game,
        ClientEvent.TICK_TOPIC: adapter.tick_topic,
        ClientEvent.UNTICK_TOPIC: adapter.untick_topic,
        ClientEvent.CLAIM_PRIZE: adapter.claim_prize,
    }
    for event, command in commands.items():
        server.on(event.value, command)
    server.on("disconnect", adapter.disconnect)

    return server
