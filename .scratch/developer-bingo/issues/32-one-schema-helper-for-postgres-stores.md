# 32: One schema-ready and error-translation helper for the Postgres stores

**What to build:** The History Store (`history.py`) and the Pool Library (`pool_library.py`) are both Postgres adapters, and each repeats the same scaffolding:

- a process-wide lock (`_create_lock` in `history.py`, `_seed_lock` in `pool_library.py`)
- a `_TABLES` list of the model tables, each with a `# ty: ignore[missing-attribute]`
- a create-tables step that runs once, lazily, before the first call (`_ensure_tables` and `_ensure_ready`)
- a `SQLAlchemyError` translated to the store's "unavailable" error in every method

The stores differ in their queries, and in the pool library's default-pool seeding. The scaffolding should be written once, so a new Postgres-backed store, or a change to how schema is set up, is one edit.

**Blocked by:** none

**Status:** done

- [x] One helper, in its own module, creates a store's tables once, lazily, under one lock, and runs its work inside the error translation. Both `PostgresHistoryStore` and `PostgresPoolLibrary` use it. Each store keeps its own queries, and the pool library keeps its default-pool seeding
- [x] Each store still raises its own unavailable error (`HistoryUnavailable`, `PoolLibraryUnavailable`) with the same messages and status codes; `http_errors.py` needs no change
- [x] A store whose first attempt fails is not marked ready, so the next call tries again. This is the behaviour the pool library documents today
- [x] The `ty: ignore` comments for the model `__table__` attributes are written in one place, not once per store
- [x] The existing history and pool library tests pass unchanged, and `ruff`, `ty` and the backend test suite pass

## Notes

- Found in the architecture review of 2026-11-15 (candidate 2).
- Only the Postgres adapters are in scope. The in-memory stores have none of this scaffolding and stay as they are.
