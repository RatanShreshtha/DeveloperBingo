# 28: One source for the frontend session's exported fields

**What to build:** `frontend/src/stores/session.ts` builds one Pinia store from three factories (`createGameSession`, `createPlayerSession`, `createHostSession`). It returns about 35 keys, and then `usePlayerSession` and `useHostSession` each re-list their fields twice: once in `storeToRefs` destructuring and once in the `reactive(...)` return. A new field means editing the store, both facades, and sometimes the view. The facades only narrow what each view sees, so they add repetition without adding depth.

Reconnect dispatch is also implicit. `onReconnect` picks the role from state (`player.player.value ? player.reconnect() : host.reconnect()`), so the role is inferred from whichever value happens to be set.

**Blocked by:** none

**Status:** needs-triage

- [ ] One field list drives both facades, or the views read the store through a single typed composable per role. The field lists are written once
- [ ] Choose between two shapes and record the choice in `docs/adr/` if it changes the seam: (a) keep one store and generate the role views from its list, or (b) split into a player store and a host store that share a plain `gameSession` composable. Option (b) only works if the single transport listener moves into the shared composable
- [ ] The reconnect path names the role explicitly, set when the session is joined or hosted, instead of inferring it from state
- [ ] `PlayerPage`, `HostPage` and `JoinPage` change only their imports, if at all
- [ ] Existing store and view tests pass, with no test rewritten to hide a behaviour change

## Notes

- Found in the architecture review of 2026-11-13 (candidate 3).
- Ticket 19 merged the game session into one store. This ticket keeps that single transport listener and only removes the repetition around it.
