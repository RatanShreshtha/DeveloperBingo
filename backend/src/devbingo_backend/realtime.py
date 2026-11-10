from typing import Any, Protocol

import socketio

from devbingo_backend.game import (
    GameAlreadyStarted,
    GameError,
    GameFull,
    GameNotFound,
    GameRegistry,
    NameTaken,
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
}


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
            return {"ok": False, "error": _ERROR_CODES[type(err)]}

        await self._broadcaster.enter_room(sid, code)
        await self._broadcaster.emit(
            "lobby_updated",
            {"players": self._registry.players(code)},
            room=code,
        )
        return {"ok": True, "ticket": ticket.names()}

    async def watch_lobby(self, sid: str, payload: dict[str, str]) -> dict[str, Any]:
        code, host_token = payload["code"], payload["host_token"]
        try:
            players = self._registry.lobby(code, host_token)
        except GameError as err:
            return {"ok": False, "error": _ERROR_CODES[type(err)]}

        await self._broadcaster.enter_room(sid, code)
        return {"ok": True, "players": players}


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

    return server
