# 24: The engine builds the Game snapshot

**What to build:** `GameRegistry` returns a whole Game snapshot, one for a player and one for the host. Today it has thirteen one-line getters, and the only production caller of each is `realtime.py`, which stitches the snapshot together from seven to ten of them. `lobby()` exists only to check the host link. `GET /games/{code}/pool` has no caller, since the host's snapshot already carries the pool and its name. `pool_response` is a one-line pass-through to `PoolResponse.from_pool`.

**Blocked by:** none (22 and 23 are merged)

**Status:** ready-for-agent

### Engine

- [x] `game.py` defines frozen dataclasses. Every field is a tuple or frozenset, so no caller can change engine state through a snapshot:
  - `GameSnapshot`: `status`, `end_reason`, `players`, `draws`, `prizes` (Prize → tuple of names)
  - `PlayerSnapshot(GameSnapshot)`: adds `player` (the handle from 22), `ticket`, `ticks`, `pending_claims`, `decided_claims`
  - `HostSnapshot(GameSnapshot)`: adds `claims`, `pool`, `pool_name`, `window_open`
- [x] `registry.player_snapshot(player)` and `registry.host_snapshot(host)` return them. `host_snapshot` checks the host link
- [x] `Joined` carries the player's `PlayerSnapshot` in place of `ticket`
- [x] These are deleted from `GameRegistry`: `status`, `end_reason`, `players`, `draw_history`, `prize_board`, `claim_log`, `pool_of`, `pool_name_of`, `window_open`, `ticks`, `pending_claims`, `decided_claims` and `lobby`

### Wire and adapter

- [x] Every conversion lives in `wire.py` as a `from_*` constructor:
  - `JoinAck.from_snapshot(snapshot, rejoin_token)`
  - `WatchAck.from_snapshot(snapshot)`
  - prize board entries from a board
  - `ClaimLogEntry.from_record`
  - `ClaimSettled.from_record`
- [x] `realtime.py` keeps no conversion helpers (`_snapshot`, `_prize_board`, `_claim_entry` and `_claim_settled` are deleted). It builds `JoinAck` and the `lobby_updated` player list from what `join` returned, and `WatchAck` from `host_snapshot`
- [x] The wire messages are unchanged: the regenerated `openapi.json` differs only by the removed route and `GamePoolResponse`

### Dead code

- [x] Delete:
  - `GET /games/{code}/pool` and `GamePoolResponse`
  - `pool_response` (its callers use `PoolResponse.from_pool`)
  - `fetchGamePool` in `frontend/src/api/pools.ts` and its entry in `frontend/src/testing/apiMock.ts`
  - the game-pool cases in `test_saved_pools_api.py`

### Tests (replace, don't layer)

- [x] Tests that read the deleted getters read through the snapshots instead, for example `registry.player_snapshot(ada).ticks` or `registry.host_snapshot(game).claims`. That's about 55 call sites, mostly `ticks`, `prize_board` and `claim_log`
- [x] The snapshot-content tests in `test_session_recovery.py` move to a new `test_game_snapshot.py`, which tests through `GameRegistry` with no adapter. They cover status, players, draws, end reason and prize board, the host's pool, claims and window flag, and a player's pending and decided claims
- [x] The adapter keeps one test per acknowledgement, checking that the wire form carries the snapshot (`JoinAck`, `WatchAck`). The rejoin-token and takeover tests stay in `test_session_recovery.py`
- [x] A test checks that `host_snapshot` refuses a wrong host token

## Notes

- Glossary: "Game snapshot" already names the concept. `GameSnapshot` exists in both `game.py` (the engine's form) and `wire.py` (the wire's form), deliberately.
- Found in the architecture review of 2026-11-12 (candidate 3).
