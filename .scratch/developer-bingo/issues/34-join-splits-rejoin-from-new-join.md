# 34: Rejoin and new join are separate paths in the registry

**What to build:** `GameRegistry.join` (`game.py`, around lines 311-362) handles three cases in one method:

- a name held by a connected player: refused as `NameTaken` unless the join shows that player's rejoin token, which takes the name over
- a name held by a dropped player, or taken over with the token: the player comes back, and the join is a rejoin
- any other name: a new player, which needs the lobby, room in the game, and a dealt ticket

The three cases share the connection handling and the token issue, but each branch reads a different set of rules. The method is about 50 lines, and it is the one place the rules for who may enter a game are written, so a change to one case means reading all three. Write the rejoin case and the new-join case as two private methods, with the shared steps in one place.

**Blocked by:** none

**Status:** done

- [x] `join` decides between the rejoin path and the new-join path, and each path is its own private method. The public signature and every `join` outcome are unchanged
- [x] The rejoin path keeps the takeover rule: a connected name is refused unless the rejoin token matches, and a match replaces the old connection and reports it in `Joined.replaced`
- [x] The new-join path keeps its gates in the same order: not ended, then lobby, then the player limit, then a unique ticket
- [x] The existing rejoin, takeover, game-full, lobby and status-gate tests pass unchanged, including `test_status_gates.py` and `test_rejoin.py`
- [x] `ruff`, `ty` and the backend test suite pass

## Notes

- Found in the architecture review of 2026-11-15 (lower-priority item, not written up at the time).
- Ticket 25 moved the player join to one path in the adapter. This ticket is inside the engine and does not change the adapter.
- Keep the behaviour: the existing tests decide it, so write no new behaviour here.
