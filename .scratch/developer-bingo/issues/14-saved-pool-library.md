# 14: Saved pool library

**What to build:** The host copies the default pool, edits it, saves it to a shared library, and picks a saved pool for a game.

**Blocked by:** 03 (Pool model and the default pool), 20 (Pool per game)

**Status:** ready-for-agent

- [x] The host can copy the default pool into a custom pool
- [x] A custom pool is validated against the pool rules before saving
- [x] A saved pool is shared across all hosts
- [x] The host can pick a saved pool when setting up a game
- [x] The default pool remains read-only
