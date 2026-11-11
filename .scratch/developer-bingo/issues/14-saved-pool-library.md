# 14: Saved pool library

**What to build:** The host copies the default pool, edits it, saves it to a shared library, and picks a saved pool for a game.

**Blocked by:** 03 (Pool model and the default pool), 20 (Pool per game)

**Status:** ready-for-agent

- [ ] The host can copy the default pool into a custom pool
- [ ] A custom pool is validated against the pool rules before saving
- [ ] A saved pool is shared across all hosts
- [ ] The host can pick a saved pool when setting up a game
- [ ] The default pool remains read-only
