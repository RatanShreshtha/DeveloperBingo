# 29: One helper for the realtime adapter's command shape

**What to build:** Most handlers in `RealtimeAdapter` (`realtime.py`) follow one shape: parse the payload, call the registry, turn a `GameError` into a refusal, then publish the outcome. `start_game`, `draw_topic` and `end_game` repeat it almost line for line, differing only in the registry call. `claim_prize` does the same, but parses the prize enum inline (raising `UnknownPrize`) where the other handlers use `_parse`. `_change_ticks` already shows the helper pattern. The shape should be written once.

`publish` (lines 188-230) also holds the emission-order contract: host claim logs, then prize awards, then the game end, then per-claimant results, then the window flag. That order is only tested indirectly, through sockets.

**Blocked by:** none (ticket 27 changes the outcome the adapter reads, so coordinate if they run together)

**Status:** ready-for-agent

- [x] `_host_command` takes the payload, the registry call, an `announce` step that picks the outcome, and a `reply` step that builds the ack. `start_game`, `draw_topic` and `end_game` each call it with one line. The publish step is not optional: all three host commands announce an outcome, so the helper always publishes. `start_game` and `end_game` pass `_already_an_outcome`, since the registry already returns the outcome
- [x] The prize name is checked by `_prize_named`, which raises `UnknownPrize`. The claim payload still goes through `_parse`. The model's `prize` field stays a string on purpose: typing it as `Prize` would make an unknown prize fail as `invalid_message` instead of `unknown_prize`, which changes the wire contract
- [x] `_host_command` refuses only a `GameError`. A test checks that any other error propagates
- [x] `tests/test_publish_order.py` calls `publish` with an outcome that has every field set, and checks the emission order against the docstring's list, using the recording broadcaster

## Notes

- Found in the architecture review of 2026-11-13 (candidate 4).
- `_emit` deliberately logs and swallows a failed send so the rest still go out. That stays.
