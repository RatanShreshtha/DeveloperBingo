# 22: One handle per player

**What to build:** The engine decides which player a join refers to, and every other module uses the engine's answer. Today names are matched without regard to case or surrounding spaces in two places: `game.py` `join` and `realtime.py` `_replace_sockets_of`. The adapter also keys its socket table (`_sessions`) and its held claim answers (`_held`) by the name the client *typed*, while the engine records the *stored* name (stripped, as first joined). So a player who joins as `"Ada "`, or rejoins as `"ada"`, and wins a claim never gets an answer: `_answer_held` raises `KeyError` on `decided[name]` (`realtime.py:343`) and the claim's acknowledgement hangs, while the prize board already shows `Ada`.

**Blocked by:** none

**Status:** ready-for-agent

- [x] `GameRegistry.join` returns a canonical player handle (the game code and the stored name) as part of `Joined`
- [x] The adapter stores that handle for each socket and uses it for every later command. Held claim answers are keyed by it
- [x] `_replace_sockets_of` compares handles, not names. `name_key` is called only inside the engine
- [x] `JoinAck` carries the stored name, and the frontend session store uses it in place of what the player typed
- [x] Regression tests: join as `"Ada "`, claim a prize and close the window, and the claim is answered. Join as `"Ada"`, claim, rejoin as `"ada"` with the rejoin token while the claim waits, close the window, and the claim is answered

## Notes

- Ticket 23 builds on this: claim results there are sent to whichever socket holds the player's handle.
- Found during the architecture review of 2026-11-12 (candidate 1).
