# 27: Game status checks and window transitions live with the game

**What to build:** `GameRegistry` (`game.py`, about 370 lines) does four jobs: lobby and identity (`join`, rejoin, connections), status gating, draws, ticks and claims, and snapshot assembly. Two parts of it are repeated or hand-computed:

- The "is the game started, or ended?" checks are repeated in `start`, `draw`, `tick`, `untick`, `claim` and `_game_refusal`, with `_refuse_if_ended` and `status != "started"` written out each time.
- The settlement-window flag is computed by hand in three places. `end` uses `window_open=False if was_open else None`. `claim` uses `True if not was_open else None`. `_close_window` uses `None if game.settlement.window_open() else False`. The adapter then emits `WINDOW_CHANGED` only when the flag is not `None`.

**Blocked by:** none

**Status:** needs-triage

- [ ] Each command that needs a status (`start`, `draw`, `tick`, `untick`, `claim`) asks `_Game` for it, for example `game.require_started()` or `game.require_not_ended()`. The rule "which commands are allowed in which status" then lives in one place
- [ ] `ClaimSettlement` reports window transitions in its own result, for example a `WindowTransition` of opened, closed, or unchanged. `end`, `claim` and `_close_window` pass that through instead of each comparing before and after
- [ ] The `Outcome.window_open` values the adapter sees are unchanged, so `WINDOW_CHANGED` is still sent only on a real transition. The existing tests for the window flag pass without edits
- [ ] A test per status gate checks that a command in the wrong status is refused with the same error code as before
- [ ] Do not split the registry into separate classes in this ticket. Only one implementation of each part exists, so a new seam would be hypothetical

## Notes

- Found in the architecture review of 2026-11-13 (candidate 2).
- Related: ticket 24 moved snapshot assembly into the engine. The snapshot helpers stay where they are.
