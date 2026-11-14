# The engine reports an ended game's summary in its outcome, and the socket adapter keeps it off the event loop

**Status:** accepted

**Context:** When a game ended, the engine called its `on_ended` observer synchronously, and that observer saved the game to Postgres. The engine runs inside async socket handlers, so every game end blocked the server's event loop for the length of the database write: up to the two-second connect timeout when Postgres was slow or down. A failed save was logged and dropped, so the host got no signal that the game's history was lost.

**Decision:** The engine has no outbound storage call. `_end` returns the game's `GameSummary`, and the outcome that ends the game carries it in `Outcome.summary`. `RealtimeAdapter` announces the end to the room first, then hands the summary to its `on_ended` keeper on a worker thread (`asyncio.to_thread`). A keeper failure is logged and goes no further, because the game has already ended. The keeper is wired through `build_socket_server`, so the app keeps history on the same path every live game takes.

We considered making `on_ended` async and awaited by the engine. We chose the outcome instead, because the engine already reports every state change through `Outcome`, and this keeps the engine free of I/O.

**Consequences:**
- The command that ends a game (`end_game`, `draw_topic`, `claim_prize`, or a timed full-house close) returns only after the save finishes. Other players' commands are served while the save runs.
- A game that ends in the engine without going through the adapter is not saved. Tests that need history must end the game through the adapter.
- A failed save is logged, not retried, and the host is not told. This matches the earlier behaviour.
- `GameRegistry` no longer takes an `on_ended` argument.
