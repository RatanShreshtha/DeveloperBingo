# 31: One function ends a game

**What to build:** Two paths end a game in `GameRegistry` (`game.py`). `end` (around lines 408-418) closes every open settlement window with the `game_ended` refusal, calls `_end`, and builds the `Outcome`. The full-house branch of `_close_window` (around lines 495-505) does the same: it closes the other windows with the same refusal, calls `_end`, and builds the `Outcome`. The two assemblies differ only in the reason, and in where the window flag comes from: `end` takes it from `close_all`, while the full-house branch hard-codes `window_open=False`.

Write the ending once, as one private function that takes the reason and returns the outcome. A change to what an ended game announces then happens in one place.

**Blocked by:** none

**Status:** done

- [x] One private function in `game.py` ends a game for both `end` and the full-house branch of `_close_window`. It closes the remaining windows, calls `_end`, and returns the `Outcome`
- [x] Both paths give the same `Outcome` as before: the same `settled` tuple, `ended`, `window_open` and `summary`. The full-house path keeps `window_open=False`, which is what `close_all` reports there, so no test changes
- [x] The existing tests for host end, full house and settlement-with-end pass unchanged
- [x] `ruff`, `ty` and the backend test suite pass

## Notes

- Found in the architecture review of 2026-11-15 (candidate 1).
- The shared function must still close windows before `_end` runs, because `_end` builds the summary from the game as it stands.
