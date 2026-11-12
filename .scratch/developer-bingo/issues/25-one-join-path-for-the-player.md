# 25: One join path for the player

**What to build:** The session store joins a game in one way, whichever way the join started, with each failure handled according to one table. Today `join`, `resume` and `rejoin` (run by `recover` on reconnect) each send `join_game` and enter, but each fails differently:
- A fresh join throws when the server can't be reached.
- A refused reconnect only sets `actionError`, so a player whose game is gone (`not_found` after a server restart) stays on a dead game.
- A reconnect that can't reach the server is an unhandled rejection.

`PlayerLobbyView` also decides whether to show the game from a local `canPlay` set once on mount, so it couldn't show the player leaving even if the store dropped them.

**Blocked by:** none (frontend only; independent of 24)

**Status:** ready-for-agent

### Store

- [x] `join`, `resume` and `recover` all go through one private `enterGame(code, name, how)`, where `how` is `'fresh' | 'reload' | 'reconnect'`. Reload uses the saved rejoin token; reconnect uses the one in memory
- [x] What each failure does comes from one table in the store:

  | How | Refused | Server unreachable |
  |---|---|---|
  | fresh | `error`, nothing saved | `error` = unreachable message, nothing saved |
  | reload | leave the game (forget saved), `error` | `error`, keep the saved session |
  | reconnect | leave the game (clear player, forget saved), `error` | `actionError`, keep player and saved session; the next reconnect tries again |

- [x] Nothing throws out of `join`, `resume` or the reconnect handler
- [x] One `leave(reason)` handles being replaced and a refused reload or reconnect. It clears the player and ticket, forgets the saved session, and sets `replaced` or `error`. The `replaced` listener uses it
- [x] The store's public state is unchanged (`player`, `replaced`, `error`, `actionError`). `resume` still returns at once when the player is already in that game
- [x] `savedSession.ts` stays as its own module

### View

- [x] `PlayerLobbyView` drops `canPlay`. It shows the game only while `store.player` is set for this code; otherwise it shows why (replaced, or `store.error`) and the "Join this game" link

### Tests (replace, don't layer)

- [x] One table-driven test (in its own file, `sessionJoin.test.ts`) covers the nine cases: fresh, reload and reconnect, each answered with a snapshot, a refusal, or a thrown error. It checks `player`, `error`, `actionError` and the saved session
- [x] The per-path join tests in `sessionRecovery.test.ts` and `sessionReconnect.test.ts` that the table duplicates are deleted
- [x] A view test checks that after a refused reconnect, `PlayerLobbyView` shows the error and the "Join this game" link

## Notes

- Found in the architecture review of 2026-11-12 (candidate 4), and earlier in the ticket 19 spec review ("`rejoin()` on reconnect … the player stays on a dead game").
