import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import socketio
from pydantic import BaseModel, TypeAdapter, ValidationError

from devbingo_backend.game import (
    GameError,
    GameRegistry,
    GameSummary,
    HostLink,
    InvalidMessage,
    Outcome,
    PlayerRef,
    UnknownPrize,
)
from devbingo_backend.prizes import Prize
from devbingo_backend.settlement import ClaimRecord
from devbingo_backend.wire import (
    Accepted,
    ClaimLogEntry,
    ClaimPayload,
    ClaimSettled,
    ClaimWaiting,
    ClientEvent,
    DrawAck,
    DrawAnnouncement,
    GameEnded,
    GameStarted,
    JoinAck,
    JoinPayload,
    LobbyUpdated,
    PrizeAwarded,
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


logger = logging.getLogger(__name__)

Ack = dict[str, Any]


def _refusal(err: GameError) -> Ack:
    """The acknowledgement that tells only the sender why a request was refused."""
    return Refusal(error=err.code).model_dump(mode="json")


def _parse[M](model: type[M], payload: object) -> M:
    """Reads a payload into its model. A bad or missing field refuses the whole message."""
    try:
        return TypeAdapter(model).validate_python(payload)
    except ValidationError:
        raise InvalidMessage from None


def _host_room(code: str) -> str:
    """The room only the game's host sockets are in. The game's own room has every player too."""
    return f"{code}:host"


class RealtimeAdapter:
    """Turns socket events into engine calls and engine state into room broadcasts.

    Holds no game rules: the registry decides, the adapter only reports. It hears the outcome of
    every settlement window that closes on time, and announces it like a command's own outcome.
    """

    def __init__(
        self,
        registry: GameRegistry,
        broadcaster: Broadcaster,
        on_ended: Callable[[GameSummary], None] | None = None,
    ) -> None:
        """`on_ended` keeps each ended game's summary, such as in stored history. It runs on a
        worker thread after the room hears the end, so a slow store does not hold up other players."""
        self._registry = registry
        self._broadcaster = broadcaster
        self._on_ended = on_ended
        registry.listen(self.publish)

    async def join_game(self, sid: str, payload: object) -> Ack:
        try:
            message = _parse(JoinPayload, payload)
            joined = self._registry.join(
                PlayerRef(code=message.code, name=message.name),
                message.rejoin_token,
                sid,
            )
        except GameError as err:
            return _refusal(err)

        # From here on the player is the one the game knows, not the name as this client typed it.
        snapshot = joined.snapshot
        player = snapshot.player

        for old in joined.replaced:
            await self._broadcaster.leave_room(old, player.code)
            await self._emit(player.code, ServerEvent.REPLACED, Replaced(), to=old)
        # In the room first, so the joiner hears the lobby change they caused.
        await self._broadcaster.enter_room(sid, player.code)
        await self.publish(player.code, joined.outcome)
        # A rejoin restores the ticks the player already had, so they come back here.
        return JoinAck.from_snapshot(snapshot, joined.rejoin_token).model_dump(
            mode="json"
        )

    async def disconnect(self, sid: str) -> None:
        """A socket has dropped. The player keeps their place and can rejoin by name."""
        self._registry.drop(sid)

    async def watch_lobby(self, sid: str, payload: object) -> Ack:
        try:
            host = _parse(HostLink, payload)
            snapshot = self._registry.host_snapshot(host)
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.enter_room(sid, host.code)
        await self._broadcaster.enter_room(sid, _host_room(host.code))
        return WatchAck.from_snapshot(snapshot).model_dump(mode="json")

    async def start_game(self, sid: str, payload: object) -> Ack:
        try:
            host = _parse(HostLink, payload)
            outcome = self._registry.start(host)
        except GameError as err:
            return _refusal(err)

        await self.publish(host.code, outcome)
        return Accepted().model_dump(mode="json")

    async def draw_topic(self, sid: str, payload: object) -> Ack:
        try:
            host = _parse(HostLink, payload)
            drawn = self._registry.draw(host)
        except GameError as err:
            return _refusal(err)

        await self.publish(host.code, drawn.outcome)
        return DrawAck(draw=DrawAnnouncement.from_draw(drawn.draw)).model_dump(
            mode="json"
        )

    async def end_game(self, sid: str, payload: object) -> Ack:
        """The host ends the game. Windows still open settle at once, refused; everyone in the room is told."""
        try:
            host = _parse(HostLink, payload)
            outcome = self._registry.end(host)
        except GameError as err:
            return _refusal(err)

        await self.publish(host.code, outcome)
        return Accepted().model_dump(mode="json")

    async def claim_prize(self, sid: str, payload: object) -> Ack:
        """A refused claim is told to the claimant at once, and logged for the host. A valid one
        waits in the prize's settlement window: it is acknowledged as waiting, and its result goes to
        the claimant as `claim_settled` when the window closes, on whichever socket holds them then."""
        try:
            message = _parse(ClaimPayload, payload)
            player = self._registry.player_on(sid)
            try:
                prize = Prize(message.prize)
            except ValueError:
                raise UnknownPrize from None
            result = self._registry.claim(player, prize)
        except GameError as err:
            return _refusal(err)

        await self.publish(player.code, result.outcome)
        if result.refusal is not None:
            return _refusal(result.refusal)
        return ClaimWaiting().model_dump(mode="json")

    async def publish(self, code: str, outcome: Outcome) -> None:
        """Announces what an outcome changed. The room hears a lobby change, the game's start, each
        topic drawn, the winners and the game's end. The host hears each decided claim (those refused
        on arrival and those a closed window settled) and when the window state changed. Each
        claimant hears their own result. Each emit is tried on its own, so one that fails is logged
        and the rest still go out."""
        if outcome.lobby is not None:
            lobby = LobbyUpdated(players=list(outcome.lobby))
            await self._emit(code, ServerEvent.LOBBY_UPDATED, lobby, room=code)
        if outcome.started:
            await self._emit(code, ServerEvent.GAME_STARTED, GameStarted(), room=code)
        if outcome.drawn is not None:
            announcement = DrawAnnouncement.from_draw(outcome.drawn)
            await self._emit(code, ServerEvent.TOPIC_DRAWN, announcement, room=code)
        for record in outcome.decided:
            await self._tell_host(code, record)
        for settled in outcome.settled:
            for record in settled.records:
                await self._tell_host(code, record)
        for settled in outcome.settled:
            if settled.awarded_to:
                award = PrizeAwarded(
                    prize=settled.prize, awarded_to=list(settled.awarded_to)
                )
                await self._emit(code, ServerEvent.PRIZE_AWARDED, award, room=code)
        if outcome.ended is not None:
            await self._emit(
                code, ServerEvent.GAME_ENDED, GameEnded(reason=outcome.ended), room=code
            )
        for settled in outcome.settled:
            for record in settled.records:
                for sid in self._registry.connections_of(
                    PlayerRef(code, record.player)
                ):
                    result = ClaimSettled.from_record(record)
                    await self._emit(code, ServerEvent.CLAIM_SETTLED, result, to=sid)
        if outcome.window_open is not None:
            await self._emit(
                code,
                ServerEvent.WINDOW_CHANGED,
                WindowChanged(open=outcome.window_open),
                room=_host_room(code),
            )
        # Last, so the room hears the end before the save starts.
        if outcome.summary is not None:
            await self._keep_ended(code, outcome.summary)

    async def _keep_ended(self, code: str, summary: GameSummary) -> None:
        """Hands an ended game to `on_ended` on a worker thread. A failure is logged and goes no
        further: the game has already ended."""
        if self._on_ended is None:
            return
        try:
            await asyncio.to_thread(self._on_ended, summary)
        except Exception:
            logger.exception("could not keep the summary of game %s", code)

    async def _emit(
        self,
        code: str,
        event: ServerEvent,
        message: BaseModel,
        room: str | None = None,
        to: str | None = None,
    ) -> None:
        """Sends one message. A failure is logged and goes no further."""
        try:
            await self._broadcaster.emit(
                event, message.model_dump(mode="json"), room=room, to=to
            )
        except Exception:
            logger.exception("could not send %s in game %s", event.value, code)

    async def _tell_host(self, code: str, record: ClaimRecord) -> None:
        """Sends the host one decided claim, and nobody else."""
        entry = ClaimLogEntry.from_record(record)
        await self._emit(code, ServerEvent.CLAIM_LOGGED, entry, room=_host_room(code))

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
            change(self._registry.player_on(sid), message.topic)
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
    registry: GameRegistry, on_ended: Callable[[GameSummary], None] | None = None
) -> tuple[socketio.AsyncServer, RealtimeAdapter]:
    """The socket server, and the adapter behind it. `on_ended` keeps each ended game's summary."""
    server = socketio.AsyncServer(async_mode="asgi")
    adapter = RealtimeAdapter(registry, _SocketIOBroadcaster(server), on_ended)

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

    return server, adapter
