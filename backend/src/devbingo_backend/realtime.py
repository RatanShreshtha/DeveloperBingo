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
    PlayerRef,
    UnknownPrize,
)
from devbingo_backend.prizes import Prize
from devbingo_backend.wire import (
    Accepted,
    ClaimPayload,
    ClientEvent,
    DrawAck,
    DrawAnnouncement,
    GameStarted,
    HostLink,
    JoinAck,
    JoinPayload,
    LobbyUpdated,
    PrizeAwarded,
    PrizeBoardEntry,
    Refusal,
    ServerEvent,
    TickPayload,
    WatchAck,
)


class Broadcaster(Protocol):
    """The part of the Socket.IO server the adapter needs, so tests can fake it."""

    async def enter_room(self, sid: str, room: str) -> None: ...

    async def emit(
        self,
        event: str,
        data: Any,
        room: str | None = None,
        to: str | None = None,
    ) -> None: ...


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


def _prize_board(board: dict[Prize, str | None]) -> list[PrizeBoardEntry]:
    """The prize board in the order the engine keeps it."""
    return [PrizeBoardEntry(prize=prize, awarded_to=name) for prize, name in board.items()]


class RealtimeAdapter:
    """Turns socket events into engine calls and engine state into room broadcasts.

    Holds no game rules: the registry decides, the adapter only reports.
    """

    def __init__(self, registry: GameRegistry, broadcaster: Broadcaster) -> None:
        self._registry = registry
        self._broadcaster = broadcaster
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
            player = PlayerRef(code=message.code, name=message.name)
            lobby_size = len(self._registry.players(player.code))
            ticket = self._registry.join(player)
        except GameError as err:
            return _refusal(err)

        self._sessions[sid] = player
        await self._broadcaster.enter_room(sid, player.code)
        # Only a new player changes the lobby. A rejoin changes nothing for the others.
        if len(self._registry.players(player.code)) != lobby_size:
            await self._broadcaster.emit(
                ServerEvent.LOBBY_UPDATED,
                LobbyUpdated(players=self._registry.players(player.code)).model_dump(mode="json"),
                room=player.code,
            )
        # A rejoin restores the ticks the player already had, so they come back here.
        return JoinAck(
            ticket=ticket.to_cells(),
            ticks=sorted(self._registry.ticks(player)),
            prizes=_prize_board(self._registry.prize_board(player.code)),
        ).model_dump(mode="json")

    async def disconnect(self, sid: str) -> None:
        """A socket has dropped. The player keeps their place and can rejoin by name."""
        player = self._sessions.pop(sid, None)
        if player is not None:
            self._registry.disconnect(player)

    async def watch_lobby(self, sid: str, payload: object) -> Ack:
        try:
            host = _parse(HostLink, payload)
            players = self._registry.lobby(host)
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.enter_room(sid, host.code)
        return WatchAck(
            players=players,
            prizes=_prize_board(self._registry.prize_board(host.code)),
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

    async def claim_prize(self, sid: str, payload: object) -> Ack:
        """A valid claim is announced to the whole room. A refused one is told to the claimant only."""
        try:
            message = _parse(ClaimPayload, payload)
            player = self._player_on(sid)
            try:
                prize = Prize(message.prize)
            except ValueError:
                raise UnknownPrize from None
            self._registry.claim(player, prize)
        except GameError as err:
            return _refusal(err)

        winner = self._registry.prize_board(player.code)[prize]
        assert winner is not None  # the claim just awarded it
        await self._broadcaster.emit(
            ServerEvent.PRIZE_AWARDED,
            PrizeAwarded(prize=prize, winner=winner).model_dump(mode="json"),
            room=player.code,
        )
        return Accepted().model_dump(mode="json")

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
        ClientEvent.TICK_TOPIC: adapter.tick_topic,
        ClientEvent.UNTICK_TOPIC: adapter.untick_topic,
        ClientEvent.CLAIM_PRIZE: adapter.claim_prize,
    }
    for event, command in commands.items():
        server.on(event.value, command)
    server.on("disconnect", adapter.disconnect)

    return server
