# 07: Rejoin with the same name

**What to build:** A player who drops and rejoins with the same name gets the same ticket and the same ticks back.

**Blocked by:** 06 (Tick drawn topics)

**Status:** ready-for-agent

- [x] Rejoining with the same name before the game ends restores the ticket (a rejoin is allowed even after the game has started; a new name is not)
- [x] Rejoining restores the player's ticks
- [x] A rejoin with a name that belongs to no one in the game is treated as a new join, not a restore
- [ ] A rejoin is not possible after the game ends (waits for issue 13)
