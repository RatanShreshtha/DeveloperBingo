# 33: The game session owns the game's status transitions

**What to build:** The frontend's game status changes in three modules:

- `gameSession.ts` owns `recordEnd` and the `game_started` listener, which moves the status to `started` only from `lobby`.
- `session.ts` (the store's composition root) listens for `game_ended` and calls `game.recordEnd`, so the end listener sits outside the module that owns the end.
- `hostSession.ts` `start()` writes `game.status.value = 'started'` directly after the server accepts the start, bypassing the guard the `game_started` listener has. It also calls `game.recordEnd('host')` after a host end.

So the rule for how a game's status moves is written in two places, and the host session reaches into the game session's state. Moving the transitions into `gameSession.ts` as named functions leaves one place that moves the status, and the host and composition modules only ask for the transition.

**Blocked by:** none

**Status:** done

- [x] `gameSession.ts` exposes `markStarted()` and `recordEnd(reason)`, and owns the `game_ended` listener beside them. `session.ts` no longer listens for `game_ended`
- [x] `hostSession.ts` `start()` and `end()` call `markStarted()` and `recordEnd('host')`; no host code writes `game.status` directly
- [x] `markStarted()` keeps the guard: it moves the status to `started` only from `lobby`, so a late acknowledgement cannot move an ended game back
- [x] The public shape of the session stores does not change: `usePlayerSession()` and `useHostSession()` expose the same fields, and no view changes
- [x] The existing session tests pass unchanged, and `npm run lint`, `npm run typecheck` and `npm run test` pass

## Notes

- Found in the architecture review of 2026-11-15 (candidate 3).
- Ticket 28 split the views and named the roles. This ticket moves only the status transitions and does not touch the views.
