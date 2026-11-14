# 28: One source for the frontend session's exported fields

**What to build:** `frontend/src/stores/session.ts` builds one Pinia store from three factories (`createGameSession`, `createPlayerSession`, `createHostSession`). It returns about 35 keys, and then `usePlayerSession` and `useHostSession` each re-list their fields twice: once in `storeToRefs` destructuring and once in the `reactive(...)` return. A new field means editing the store, both facades, and sometimes the view. The facades only narrow what each view sees, so they add repetition without adding depth.

Reconnect dispatch is also implicit. `onReconnect` picks the role from state (`player.player.value ? player.reconnect() : host.reconnect()`), so the role is inferred from whichever value happens to be set.

**Blocked by:** none

**Status:** ready-for-agent

- [x] Each view is built by `viewOf` from its own field list (`PLAYER_VIEW`, `HOST_VIEW`). The nine fields both roles read are listed once, in `SHARED_VIEW`, which both lists spread in. The store lists every field once, and a view names only the fields it reads
- [x] Shape (a) was chosen: one store with generated role views. The seam is unchanged (`usePlayerSession` and `useHostSession` keep their signatures), so no ADR was needed. Shape (b) would have moved the transport listener, which ticket 19 merged into one store on purpose
- [x] The reconnect path names the role explicitly. `gameSession` holds a `roles` set: a join adds `'player'`, a leave removes it, and watching as host adds `'host'`. Reconnect checks the `'player'` role first, as before
- [x] No view changed. `PlayerPage`, `HostPage` and `JoinPage` are untouched
- [x] Existing tests pass unchanged. One characterization test was added before the change: a tab that watches as host and whose player is replaced reconnects as host. The existing test that a tab with both roles recovers only its player still holds

## Notes

- Found in the architecture review of 2026-11-13 (candidate 3).
- Ticket 19 merged the game session into one store. This ticket keeps that single transport listener and only removes the repetition around it.
