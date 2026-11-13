"""Who holds each live connection: the one record of which players are connected.

A connection is an opaque id the caller chooses, such as a socket's. A player holds at most one
connection at a time: a new one replaces the old, and the old one's later drop changes nothing.
So "this player is connected" and "this connection is theirs" are one fact, kept here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from devbingo_backend.errors import NotJoined

if TYPE_CHECKING:  # the engine owns a Connections, so it is only named here, not imported
    from devbingo_backend.game import PlayerRef


class Connections:
    def __init__(self) -> None:
        self._player_on: dict[str, PlayerRef] = {}

    def holds(self, connection: str) -> bool:
        """True when this connection already belongs to a player."""
        return connection in self._player_on

    def player_on(self, connection: str) -> PlayerRef:
        """The player this connection belongs to. Raises NotJoined for one that joined no one."""
        try:
            return self._player_on[connection]
        except KeyError:
            raise NotJoined from None

    def held_by(self, player: PlayerRef) -> tuple[str, ...]:
        """Every connection this player holds now: none, or one."""
        return tuple(held for held, who in self._player_on.items() if who == player)

    def is_connected(self, player: PlayerRef) -> bool:
        return bool(self.held_by(player))

    def attach(self, connection: str, player: PlayerRef) -> tuple[str, ...]:
        """Give the connection to the player. The connection must not belong to a player yet: the
        caller checks `holds` first. Returns the connections the player held before, now replaced: none for a first join."""
        replaced = self.held_by(player)
        for old in replaced:
            del self._player_on[old]
        self._player_on[connection] = player
        return replaced

    def detach(self, connection: str) -> PlayerRef | None:
        """The connection has dropped. Returns the player it was holding, who is now not connected,
        or None when it held no one: it never joined, or a newer connection replaced it."""
        return self._player_on.pop(connection, None)

    def drop_player(self, player: PlayerRef) -> None:
        """The player is not connected, whichever connection they held."""
        for held in self.held_by(player):
            del self._player_on[held]
