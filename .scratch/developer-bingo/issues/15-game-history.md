# 15: Game history

**What to build:** When a game ends, its draws, claims and winners are stored. Anyone with the game's ID can view them.

**Blocked by:** 13 (End the game), 21 (Host sees every claim)

**Status:** ready-for-agent

- [x] An ended game stores its draws in order
- [x] An ended game stores its claims with their outcomes
- [x] An ended game stores its winners
- [x] The stored history can be viewed by game ID
- [x] The stored history round-trips correctly

## Notes
- Ticket 13 ends a game in one place, `GameRegistry._end`, whether the host ended it or the full house was awarded. Saving the history belongs there, so neither path can skip it.
