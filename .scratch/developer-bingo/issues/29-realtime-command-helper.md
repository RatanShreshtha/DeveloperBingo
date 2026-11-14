# 29: One helper for the realtime adapter's command shape

**What to build:** Most handlers in `RealtimeAdapter` (`realtime.py`) follow one shape: parse the payload, call the registry, turn a `GameError` into a refusal, then publish the outcome. `start_game`, `draw_topic` and `end_game` repeat it almost line for line, differing only in the registry call. `claim_prize` does the same, but parses the prize enum inline (raising `UnknownPrize`) where the other handlers use `_parse`. `_change_ticks` already shows the helper pattern. The shape should be written once.

`publish` (lines 188-230) also holds the emission-order contract: host claim logs, then prize awards, then the game end, then per-claimant results, then the window flag. That order is only tested indirectly, through sockets.

**Blocked by:** none (ticket 27 changes the outcome the adapter reads, so coordinate if they run together)

**Status:** needs-triage

- [ ] A host-command helper takes the payload model, the registry call, and an optional publish step. `start_game`, `draw_topic` and `end_game` use it. Each handler body is the registry call and nothing else
- [ ] `claim_prize` parses the prize through a model or helper that raises `UnknownPrize`, so every payload goes through `_parse`
- [ ] The helpers keep the refusal behaviour: a `GameError` becomes `_refusal(err)`, and nothing else is caught
- [ ] A test calls `publish` with an outcome that has every field set, and checks the emission order against the list in the docstring, with a fake broadcaster that records calls

## Notes

- Found in the architecture review of 2026-11-13 (candidate 4).
- `_emit` deliberately logs and swallows a failed send so the rest still go out. That stays.
