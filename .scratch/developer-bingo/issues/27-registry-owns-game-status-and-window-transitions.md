# 27: Game status checks and window transitions live with the game

**What to build:** `GameRegistry` (`game.py`, about 370 lines) does four jobs: lobby and identity (`join`, rejoin, connections), status gating, draws, ticks and claims, and snapshot assembly. Two parts of it are repeated or hand-computed:

- The "is the game started, or ended?" checks are repeated in `start`, `draw`, `tick`, `untick`, `claim` and `_game_refusal`, with `_refuse_if_ended` and `status != "started"` written out each time.
- The settlement-window flag is computed by hand in three places. `end` uses `window_open=False if was_open else None`. `claim` uses `True if not was_open else None`. `_close_window` uses `None if game.settlement.window_open() else False`. The adapter then emits `WINDOW_CHANGED` only when the flag is not `None`.

**Blocked by:** none

**Status:** ready-for-agent

- [x] Each command that needs a status asks `_Game` for its gate: `require_not_ended()`, `require_lobby()`, `require_started()`, and `claim_refusal()` for claims, which logs the refusal instead of raising. `_refuse_if_ended` and `_game_refusal` are deleted
- [x] `ClaimSettlement` reports the game-wide window change in its own results: `Pending.window`, `Settled.window`, and `close_all()` returns it for a whole call. The change is True when a window opened, False when the last closed, and None otherwise. The registry no longer compares before and after. `open_prizes()` is deleted
- [x] The `Outcome.window_open` values are unchanged, and no existing window-flag test was edited. `WINDOW_CHANGED` is still sent only on a real transition
- [x] `tests/test_status_gates.py` is a table of each command against each status: a status refuses with the same error as before. It was written and passed against the old code first
- [x] The registry stays one class. No new seam was added

## Notes

- Found in the architecture review of 2026-11-13 (candidate 2).
- Related: ticket 24 moved snapshot assembly into the engine. The snapshot helpers stay where they are.

## Notes

- Found in the architecture review of 2026-11-13 (candidate 2).
- Related: ticket 24 moved snapshot assembly into the engine. The snapshot helpers stay where they are.
