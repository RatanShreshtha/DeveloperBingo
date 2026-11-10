from typing import Any, Protocol

import socketio

from devbingo_backend.game import (
    ClaimNotValid,
    GameAlreadyStarted,
    GameError,
    GameFull,
    GameNotFound,
    GameNotStarted,
    GameRegistry,
    HostLink,
    NameTaken,
    NoTopicsLeft,
    NotAPlayer,
    NotHost,
    PlayerRef,
    PrizeAlreadyAwarded,
    TopicNotDrawn,
    TopicNotOnTicket,
)
from devbingo_backend.prizes import Prize
from devbingo_backend.wire import DrawAnnouncement


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


_ERROR_CODES: dict[type[GameError], str] = {
    GameNotFound: "not_found",
    NotHost: "not_host",
    NameTaken: "name_taken",
    GameFull: "game_full",
    GameAlreadyStarted: "already_started",
    GameNotStarted: "not_started",
    NoTopicsLeft: "no_topics_left",
    NotAPlayer: "not_a_player",
    TopicNotDrawn: "not_drawn",
    TopicNotOnTicket: "not_on_ticket",
    ClaimNotValid: "not_won",
    PrizeAlreadyAwarded: "prize_taken",
}


def _refusal(err: GameError) -> dict[str, Any]:
    """The acknowledgement that tells only the sender why a request was refused."""
    return {"ok": False, "error": _ERROR_CODES[type(err)]}


def _prize_board(board: dict[Prize, str | None]) -> dict[str, str | None]:
    """The prize board in the wire's terms: prize names as strings, winners by name."""
    return {prize.value: winner for prize, winner in board.items()}


def _host_link(payload: dict[str, str]) -> HostLink:
    return HostLink(code=payload["code"], token=payload["host_token"])


def _player(payload: dict[str, str]) -> PlayerRef:
    return PlayerRef(code=payload["code"], name=payload["name"])


class RealtimeAdapter:
    """Turns socket events into engine calls and engine state into room broadcasts.

    Holds no game rules: the registry decides, the adapter only reports.
    """

    def __init__(self, registry: GameRegistry, broadcaster: Broadcaster) -> None:
        self._registry = registry
        self._broadcaster = broadcaster
        # Which player each live socket belongs to, so a dropped socket frees its name.
        self._sessions: dict[str, PlayerRef] = {}

    async def join_game(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        # One socket is one player. Joining again on the same socket would leave the
        # first player connected for ever, so it is refused.
        if sid in self._sessions:
            return {"ok": False, "error": "already_joined"}
        player = _player(payload)
        try:
            lobby_size = len(self._registry.players(player.code))
            ticket = self._registry.join(player)
        except GameError as err:
            return _refusal(err)

        self._sessions[sid] = player
        await self._broadcaster.enter_room(sid, player.code)
        # Only a new player changes the lobby. A rejoin changes nothing for the others.
        if len(self._registry.players(player.code)) != lobby_size:
            await self._broadcaster.emit(
                "lobby_updated",
                {"players": self._registry.players(player.code)},
                room=player.code,
            )
        # A rejoin restores the ticks the player already had, so they come back here.
        return {
            "ok": True,
            "ticket": ticket.to_cells(),
            "ticks": sorted(self._registry.ticks(player)),
            "prizes": _prize_board(self._registry.prize_board(player.code)),
        }

    async def disconnect(self, sid: str) -> None:
        """A socket has dropped. The player keeps their place and can rejoin by name."""
        player = self._sessions.pop(sid, None)
        if player is not None:
            self._registry.disconnect(player)

    async def watch_lobby(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        try:
            players = self._registry.lobby(_host_link(payload))
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.enter_room(sid, payload["code"])
        return {
            "ok": True,
            "players": players,
            "prizes": _prize_board(self._registry.prize_board(payload["code"])),
        }

    async def start_game(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        code = payload["code"]
        try:
            self._registry.start(_host_link(payload))
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.emit("game_started", {}, room=code)
        return {"ok": True}

    async def draw_topic(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        code = payload["code"]
        try:
            draw = self._registry.draw(_host_link(payload))
        except GameError as err:
            return _refusal(err)

        announcement = DrawAnnouncement.from_draw(draw).model_dump()
        await self._broadcaster.emit("topic_drawn", announcement, room=code)
        return {"ok": True, "draw": announcement}

    # Ticks are private, and nothing is broadcast. The acknowledgement says only
    # whether the change happened: the client keeps its own list, so no ticks are
    # sent back to anyone.

    async def claim_prize(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        """A valid claim is announced to the whole room. A refused one is told to the claimant only."""
        code = payload["code"]
        try:
            prize = Prize(payload["prize"])
        except ValueError:
            return {"ok": False, "error": "unknown_prize"}
        try:
            self._registry.claim(_player(payload), prize)
        except GameError as err:
            return _refusal(err)

        winner = self._registry.prize_board(code)[prize]
        await self._broadcaster.emit(
            "prize_awarded",
            {"prize": prize.value, "winner": winner},
            room=code,
        )
        return {"ok": True}

    async def tick_topic(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        return self._change_ticks(payload, self._registry.tick)

    async def untick_topic(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        return self._change_ticks(payload, self._registry.untick)

    def _change_ticks(self, payload: dict[str, str], change: Any) -> dict[str, Any]:
        try:
            change(_player(payload), payload["topic"])
        except GameError as err:
            return _refusal(err)
        return {"ok": True}


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

    @server.event
    async def join_game(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.join_game(sid, data)

    @server.event
    async def disconnect(sid: str) -> None:
        await adapter.disconnect(sid)

    @server.event
    async def watch_lobby(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.watch_lobby(sid, data)

    @server.event
    async def start_game(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.start_game(sid, data)

    @server.event
    async def draw_topic(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.draw_topic(sid, data)

    @server.event
    async def claim_prize(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.claim_prize(sid, data)

    @server.event
    async def tick_topic(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.tick_topic(sid, data)

    @server.event
    async def untick_topic(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.untick_topic(sid, data)

    return server
