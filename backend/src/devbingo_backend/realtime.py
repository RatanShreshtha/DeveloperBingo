from typing import Any, Protocol

import socketio

from devbingo_backend.game import (
    GameAlreadyStarted,
    GameError,
    GameFull,
    GameNotFound,
    GameNotStarted,
    GameRegistry,
    NameTaken,
    NoTopicsLeft,
    NotHost,
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


_ERROR_CODES: dict[type[GameError], str] = {
    GameNotFound: "not_found",
    NotHost: "not_host",
    NameTaken: "name_taken",
    GameFull: "game_full",
    GameAlreadyStarted: "already_started",
    GameNotStarted: "not_started",
    NoTopicsLeft: "no_topics_left",
}


def _refusal(err: GameError) -> dict[str, Any]:
    """The acknowledgement that tells only the sender why a request was refused."""
    return {"ok": False, "error": _ERROR_CODES[type(err)]}


class RealtimeAdapter:
    """Turns socket events into engine calls and engine state into room broadcasts.

    Holds no game rules: the registry decides, the adapter only reports.
    """

    def __init__(self, registry: GameRegistry, broadcaster: Broadcaster) -> None:
        self._registry = registry
        self._broadcaster = broadcaster

    async def join_game(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        code, name = payload["code"], payload["name"]
        try:
            ticket = self._registry.join(code, name)
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.enter_room(sid, code)
        await self._broadcaster.emit(
            "lobby_updated",
            {"players": self._registry.players(code)},
            room=code,
        )
        return {"ok": True, "ticket": ticket.to_cells()}

    async def watch_lobby(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        code, host_token = payload["code"], payload["host_token"]
        try:
            players = self._registry.lobby(code, host_token)
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.enter_room(sid, code)
        return {"ok": True, "players": players}

    async def start_game(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        code, host_token = payload["code"], payload["host_token"]
        try:
            self._registry.start(code, host_token)
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.emit("game_started", {}, room=code)
        return {"ok": True}

    async def draw_topic(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        code, host_token = payload["code"], payload["host_token"]
        try:
            draw = self._registry.draw(code, host_token)
        except GameError as err:
            return _refusal(err)

        await self._broadcaster.emit("topic_drawn", draw.announcement(), room=code)
        return {"ok": True, "draw": draw.announcement()}

    async def get_draw_history(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        """Read the draws back for anyone catching up. Nothing is broadcast."""
        try:
            draws = self._registry.draw_history(payload["code"])
        except GameError as err:
            return _refusal(err)
        return {"ok": True, "draws": [draw.announcement() for draw in draws]}


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
    async def watch_lobby(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.watch_lobby(sid, data)

    @server.event
    async def start_game(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.start_game(sid, data)

    @server.event
    async def draw_topic(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.draw_topic(sid, data)

    @server.event
    async def get_draw_history(sid: str, data: dict[str, str]) -> dict[str, Any]:
        return await adapter.get_draw_history(sid, data)

    return server
