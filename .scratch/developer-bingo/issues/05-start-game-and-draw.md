# 05: Start the game and draw

**What to build:** The host starts the game, which closes joining and locks the pool. The host draws one topic at a time. Every player sees the draw history and each drawn topic's explanation live.

**Blocked by:** 04 (Deal tickets on join)

**Status:** ready-for-agent

- [ ] Starting the game locks the pool and closes joining (joining closes and the pool is recorded as locked; there is no pool-selection step yet, so nothing can change the pool to test against until ticket 14) — superseded: a game's pool is now fixed when the game is created (see spec.md Pool rules and ticket 20)
- [x] A draw picks uniformly at random from topics not yet drawn
- [x] A topic is never drawn twice in a game
- [x] Draws cannot happen before the game starts or after it ends (after end: delivered by ticket 13)
- [x] Draws are final, with no undo
- [x] Every player sees the draw history live, newest first
- [x] Every player sees each drawn topic's explanation
