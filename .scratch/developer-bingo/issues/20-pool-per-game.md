# 20: Pool per game

**What to build:** Each game holds the Pool it was created with, and the Pool Library is the one source of Pools. Today the engine deals and draws from the in-code `DEFAULT_POOL` (`game.py`), while the host sees the copy seeded in Postgres through `/pools/default`. The two can drift, and ticket 14 needs a game to use a saved Pool.

**Blocked by:** none

**Status:** ready-for-agent

- [x] `create_game` takes a `Pool`. Each game keeps its Pool and deals Tickets and draws from it
- [x] The engine no longer imports `DEFAULT_POOL`. `DEFAULT_POOL` stays in code only as the seed data for the Pool Library
- [x] `POST /games` loads the default Pool from the Pool Library and passes it to `create_game`
- [x] `POST /games` returns 503 when the Pool Library can't be reached. There is no fallback to the in-code Pool
- [x] The Pool Library is a port. Its interface is "load the default Pool" for now; ticket 14 adds save, list and load-by-id
- [x] Two adapters: Postgres for the app, and in-memory for tests
- [x] API tests use the in-memory adapter and no longer need Postgres
- [x] One contract test suite runs against both adapters; the Postgres run is skipped when no database is available
- [x] `GameRegistry.is_pool_locked` and its tests are removed: a game's Pool is fixed from creation, so there is nothing left to lock

## Notes

- A game's Pool is fixed from creation (spec.md, Pool rules). Tickets are dealt as players join, so changing the Pool afterwards would make their Tickets wrong. There is no "set the pool" command.
- Do this before 14.
