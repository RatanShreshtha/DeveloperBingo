# 26: Save ended games without blocking the event loop

**What to build:** When a game ends, the engine hands its summary to `on_ended`, which is `PostgresHistoryStore.save` (`app.py`). That call runs synchronously inside `GameRegistry._end` (`game.py`), which is reached from the async socket handlers (`end_game`, `draw_topic`, `claim_prize`) and the timed full-house close. So each game end does a blocking database write on the server's event loop: up to the 2-second connect timeout when Postgres is slow or down, plus the write itself. Every other player's socket waits behind it.

A failed save is caught and logged in `_end`, so a database outage loses that game's history with no signal to the host. The engine's docstring documents this as deliberate: a failing observer must never stop a game from ending. The trade-off stays, but the save should not block the loop.

**Blocked by:** none

**Status:** ready-for-agent

- [x] Decide the shape of the ended-game hand-off. Chosen: the engine returns the summary in `Outcome.summary`, and the adapter keeps it with `asyncio.to_thread`. This is neither option in the original note: the engine stays I/O-free, and the adapter already announces every outcome. Recorded in `docs/adr/0004-ended-game-summary-kept-by-the-adapter.md`
- [x] A failing keeper never stops the game from ending. The game is already ended when the keeper runs, and the failure is logged (`tests/test_ended_game_saving.py`)
- [x] A slow keeper does not hold up other commands: a test starts an end, waits for the keeper to be running on its worker thread, runs `watch_lobby`, and sees it served before the save finishes. The mutation check confirms this fails when the save runs on the loop again
- [x] The engine's `_end` docstring says nothing is stored there, and the adapter's `on_ended` docstring says a failure is logged

## Notes

- `code_has_history` (`app.py`) also runs a synchronous query inside `GameRegistry._new_code` when a game is created. The HTTP route is a sync `def`, so FastAPI runs it in the threadpool and the loop is not blocked there. Confirm that stays true if the code path moves.
- Found in the architecture review of 2026-11-13 (candidate 1).
