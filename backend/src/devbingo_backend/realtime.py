import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeVar

import socketio
from pydantic import BaseModel, ValidationError

from devbingo_backend.game import (
    AlreadyJoined,
    GameError,
    GameRegistry,
    InvalidMessage,
    NotJoined,
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
    HostLink,
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


def _host_room(code: str) -> str:
    """The room only the game's host sockets are in. The game's own room has every player too."""
    return f"{code}:host"


class RealtimeAdapter:
    """Turns socket events into engine calls and engine state into room broadcasts.

    Holds no game rules: the registry decides, the adapter only reports. It hears the outcome of
    every settlement window that closes on time, and announces it like a command's own outcome.
    """

    def __init__(self, registry: GameRegistry, broadcaster: Broadcaster) -> None:
        self._registry = registry
        self._broadcaster = broadcaster
        # Which player each live socket belongs to, so a dropped socket frees its name.
        self._sessions: dict[str, PlayerRef] = {}
        registry.listen(self.publish)

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
        snapshot = joined.snapshot
        player = snapshot.player

        if joined.took_over:
            await self._replace_sockets_of(player, keep=sid)
        self._sessions[sid] = player
        await self._broadcaster.enter_room(sid, player.code)
        # Only a new player changes the lobby. A rejoin changes nothing for the others.
        if joined.is_new_player:
            await self._broadcaster.emit(
                ServerEvent.LOBBY_UPDATED,
                LobbyUpdated(players=list(snapshot.players)).model_dump(mode="json"),
                room=player.code,
            )
        # A rejoin restores the ticks the player already had, so they come back here.
        return JoinAck.from_snapshot(snapshot, joined.rejoin_token).model_dump(mode="json")

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
            snapshot = self._registry.host_snapshot(host)
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.enter_room(sid, host.code)
        await self._broadcaster.enter_room(sid, _host_room(host.code))
        return WatchAck.from_snapshot(snapshot).model_dump(mode="json")

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
            player = self._player_on(sid)
            try:
                prize = Prize(message.prize)
            except ValueError:
                raise UnknownPrize from None
            try:
                outcome = self._registry.claim(player, prize)
            except GameError as err:
                if err.record is not None:
                    await self._tell_host(player.code, err.record)
                raise
        except GameError as err:
            return _refusal(err)

        await self.publish(player.code, outcome)
        return ClaimWaiting().model_dump(mode="json")

    async def publish(self, code: str, outcome: Outcome) -> None:
        """Announces what an outcome changed: the host hears each decided claim, the room hears the
        winners and the game's end, each claimant hears their own result, and the host hears when
        the window state changed. Each emit is tried on its own, so one that fails is logged and
        the rest still go out."""
        for settled in outcome.settled:
            for record in settled.records:
                await self._tell_host(code, record)
        for settled in outcome.settled:
            if settled.awarded_to:
                award = PrizeAwarded(prize=settled.prize, awarded_to=list(settled.awarded_to))
                await self._emit(code, ServerEvent.PRIZE_AWARDED, award, room=code)
        if outcome.ended is not None:
            await self._emit(code, ServerEvent.GAME_ENDED, GameEnded(reason=outcome.ended), room=code)
        for settled in outcome.settled:
            for record in settled.records:
                for sid in self._sockets_of(PlayerRef(code, record.player)):
                    result = ClaimSettled.from_record(record)
                    await self._emit(code, ServerEvent.CLAIM_SETTLED, result, to=sid)
        if outcome.window_open is not None:
            await self._emit(
                code,
                ServerEvent.WINDOW_CHANGED,
                WindowChanged(open=outcome.window_open),
                room=_host_room(code),
            )

    def _sockets_of(self, player: PlayerRef) -> list[str]:
        return [sid for sid, held in self._sessions.items() if held == player]

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
            await self._broadcaster.emit(event, message.model_dump(mode="json"), room=room, to=to)
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


def build_socket_server(registry: GameRegistry) -> socketio.AsyncServer:
    server = socketio.AsyncServer(async_mode="asgi")
    adapter = RealtimeAdapter(registry, _SocketIOBroadcaster(server))

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
