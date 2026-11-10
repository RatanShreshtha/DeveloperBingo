# 02: Create a game and join the lobby

**What to build:** The host creates a game and receives a private host link. Players join with a code and a unique display name, up to 200 per game, before the game starts. The lobby list updates live for everyone in the room.

**Blocked by:** 01 (Project skeleton)

**Status:** ready-for-agent

- [x] Creating a game returns a game code and a private host link
- [x] Only the host link can control the game
- [x] A player joins with a code and a display name
- [x] Names are unique within a game, and a duplicate name is rejected
- [x] The 201st join is rejected
- [x] Joins are rejected once the game starts
- [x] The lobby list updates live for all players
- [x] A thin transport test checks that a socket join becomes an engine command and a broadcast
