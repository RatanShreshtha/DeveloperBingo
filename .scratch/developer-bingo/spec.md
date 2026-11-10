Status: ready-for-agent

# DeveloperBingo

## Problem Statement

Developers who want to play together, at a meetup, in a team or online, have no quick way to run a bingo-style game built around developer, computer science and pop-culture topics. Existing bingo tools use numbers, not topics, and most require accounts or installs. A host who wants to run a round has to set everything up by hand, and players can't see a shared, live view of what's been drawn.

## Solution

A web app for a tambola-style bingo game. A host creates a game and players join it on their own devices with a name. The host draws topics one at a time from a pool. Each player holds a ticket of topics and ticks off the ones drawn. When a player has completed a prize, they claim it, and the app checks the claim against the draws. Everyone sees the draw history and the winners as they happen. The host can use the built-in default pool or a saved custom pool. No accounts are needed for players.

## User Stories

### Hosting a game

1. As a host, I want to create a new game in one step, so that I can start running a round without setup.
2. As a host, I want to receive a private host link when I create a game, so that only I can control its draws.
3. As a host, I want to choose the topic pool for a game from the built-in default or a saved custom pool, so that I can tailor the round to my audience.
4. As a host, I want to see the list of players as they join the lobby, so that I know who is ready.
5. As a host, I want to start the game when I'm ready, so that players can't join after the draws have begun.
6. As a host, I want to draw the next topic by pressing a button, so that I control the pace of the game.
7. As a host, I want each draw to be random from the topics not yet drawn, so that every game is fair.
8. As a host, I want to see the explanation of each drawn topic, so that I can read it aloud to the room.
9. As a host, I want to see every claim and whether it was accepted, so that I can follow what's happening.
10. As a host, I want to end the game at any time, so that I can stop the round when needed.
11. As a host, I want my game's draws, claims and winners saved when the game ends, so that I can review the round later.
12. As a host, I don't need a ticket of my own, so that I can concentrate on running the draws.
13. As a host, I want draws to be final, so that the game's history can't be changed after the fact.

### Joining and playing

14. As a player, I want to join a game with a code and a display name, so that I can take part without creating an account.
15. As a player, I want to receive a ticket when I join, so that I can start ticking as soon as the game begins.
16. As a player, I want my ticket to look like a tambola ticket, with three lines of five topics, so that the game feels familiar.
17. As a player, I want each column's topics shown in the same fixed order on every ticket, so that I can scan them quickly.
18. As a player, I want no two tickets in the same game to be identical, so that the game stays fair.
19. As a player, I want to tick a topic only after it has been drawn, so that I can't make a false claim by accident.
20. As a player, I want to see every topic drawn so far in the order they were drawn, so that I never miss one.
21. As a player, I want to see each drawn topic's explanation, so that I learn something while I play.
22. As a player, I want to see the prizes that are still available, so that I know what I can still win.
23. As a player, I want to see who has won each prize as soon as it's awarded, so that I stay informed about the game.
24. As a player, I want to be told when a claim is rejected, so that I know my claim didn't count.
25. As a player, I want a rejected claim to cost me nothing, so that I can keep playing.
26. As a player, I want to be able to win more than one prize in a game, so that a good ticket is rewarded.
27. As a player, I want to drop off and rejoin with the same name and get my ticket and ticks back, so that a dropped connection doesn't cost me the game.
28. As a player, I want my ticks to stay on my ticket until the game ends, so that I don't lose progress.

### Prizes and claims

29. As a player, I want to claim the top line when all five topics on it are ticked and drawn, so that I can win it.
30. As a player, I want to claim the middle line when all five topics on it are ticked and drawn, so that I can win it.
31. As a player, I want to claim the bottom line when all five topics on it are ticked and drawn, so that I can win it.
32. As a player, I want to claim the four corners when the outermost topics in the top and bottom lines are all ticked and drawn, so that I can win it.
33. As a player, I want to claim the early five when any five of my topics are ticked and drawn, so that I can win it early.
34. As a player, I want to claim the full house when every topic on my ticket is ticked and drawn, so that I can win the biggest prize.
35. As a player, I want each prize awarded only once per game, so that the prizes stay meaningful.
36. As a player, I want the first valid claim to win a prize, so that the prize goes to whoever completes it first.
37. As a player, I want two valid claims made at the same moment to both win the prize, so that a close finish isn't decided by server timing.
38. As a player, I want the game to end once the full house is claimed, so that the round has a clear conclusion.

### Pools

39. As a host, I want the default pool to be built in and read-only, so that there's always a ready-to-use pool.
40. As a host, I want to copy the default pool into a custom pool, so that I can change it without touching the default.
41. As a host, I want a custom pool to have exactly 90 distinct topics, so that the tickets and columns work the same as the default.
42. As a host, I want each topic in a custom pool to have a short explanation, so that players can learn from every draw.
43. As a host, I want the app to fill the nine columns from my pool's list in order, so that I don't have to assign topics to columns by hand.
44. As a host, I want to save a custom pool to a shared library, so that I can reuse it in later games.
45. As a host, I want to pick any saved pool from the shared library, so that I can run a game without rebuilding the pool.
46. As a host, I want the pool to lock once the first draw happens, so that the topics can't change during a game.

### Records and history

47. As a host, I want each finished game to store its draws, claims and winners, so that the round is on record.
48. As a player, I want to view a finished game's history, so that I can see how the round went.

## Implementation Decisions

### Modules

- **Game Engine** (new): the core of the game. It owns a game's full state: its lobby, its pool, its tickets, its draws, its claims, its prizes and its lifecycle. It enforces every rule in the user stories. It holds no networking code and no database code. Everything else in the system calls into it.
- **Ticket Builder** (new, inside the Game Engine): builds one ticket from the pool's columns, meeting the ticket invariants below. It is the only place that decides which topics go on a ticket.
- **Prize Evaluator** (new, inside the Game Engine): given a ticket and the draws, reports which prizes the ticket currently satisfies. Claim checks use it.
- **Pool Library** (new): stores the default pool and saved custom pools. It validates pool contents against the pool rules before saving.
- **History Store** (new): persists a finished game's draws, claims and winners, and serves them back.
- **Realtime Adapter** (new): the `python-socketio` layer. It maps incoming socket events to Game Engine commands and broadcasts the Game Engine's state changes to the right room. It contains no game rules.
- **HTTP API** (new): creates games, manages pools in the library and serves stored history. It also contains no game rules.
- **Vue frontend** (new): a lobby view for players, a host console, a player ticket view, a draw history and a prize board. It uses the generated TypeScript types from the backend's OpenAPI schema.

### Game Engine interface

The Game Engine exposes two groups of operations:

- **Commands**: create a game, join a game, set the pool, start the game, draw, tick a topic, untick a topic, claim a prize, end the game.
- **Queries**: a player's ticket view, the draw history, the prize board, the lobby list.

The engine is built with two injected dependencies, a random source and a clock, so that tests can control randomness and timing.

### Pool rules

- A pool is an ordered list of exactly 90 distinct topics, each with a short explanation. Topic names are distinct when compared case-insensitively, so "Cache" and "cache" count as the same topic.
- The nine columns are filled from the list in order. Columns 1 to 9 hold 9, 10, 10, 10, 10, 10, 10, 10 and 11 topics respectively.
- Within a column, topics appear in the same order as in the pool's list. That order is the fixed order on every ticket.
- The default pool follows the same rules. It is seeded once as a row in the database, and it is read-only: the API offers no way to change it.
- A pool locks when the first draw happens. Changing it after that is rejected.

### Ticket rules

- A ticket has three lines of five topics, and every line has exactly five topics.
- Each column contributes one to three topics to a ticket, so no column on a ticket is empty.
- A ticket has exactly fifteen topics.
- Within a column, a ticket shows its topics in the pool's order, top to bottom.
- No two tickets in the same game are identical. If the builder produces a duplicate, it builds again.
- The construction algorithm is left to the implementer. The invariants above are the contract.

### Draw rules

- A draw picks uniformly at random from the topics not yet drawn in this game.
- A topic is never drawn twice in a game.
- Draws are final. There is no undo.
- A draw cannot happen before the game starts, or after the game ends.

### Tick rules

- A player may tick a topic only if it is on their ticket and has been drawn.
- A player may untick a topic before a claim is made. (Assumption: see Further Notes.)
- A tick on an undrawn topic is rejected with an error. The tick state is not changed.

### Claim and prize rules

- A **line** prize (top, middle, bottom) is valid when every topic in that line is both ticked and drawn.
- **Four corners** is valid when the outermost topic in the top line and the outermost topic in the bottom line, on each side, are all ticked and drawn.
- **Early five** is valid when any five of the ticket's topics are ticked and drawn.
- **Full house** is valid when all fifteen topics on the ticket are ticked and drawn.
- Each prize can be awarded once per game. A player may win more than one prize.
- A rejected claim changes nothing. The player keeps playing and is told the claim was rejected.
- **Settlement window** (assumption: see Further Notes): when the first valid claim for a prize arrives, the engine opens a short window, one second by default and tunable, and holds further draws until it closes. Every valid claim for that prize received in the window wins it together. Claims are then judged against the draws at window close.
- The game ends when the full house is awarded, or when the host ends it. After it ends, no draws or claims are accepted.

### Lobby and joining

- A game is created by the host, who receives a private host link. Only that link can control the game.
- A player joins with a code and a display name. Names are unique within a game.
- A join is accepted only before the game starts. After that, joining is rejected.
- A game holds at most 200 players. A join beyond that is rejected.
- A player who drops and rejoins with the same name, before the game ends, gets the same ticket and the same ticks.
- The host holds no ticket.

### State and persistence

- A live game's state is held in memory on one server process. A restart loses live games. (See ADR 0001.)
- Finished games are persisted to the database: their draws in order, their claims with outcomes, and their winners.
- Saved pools are persisted to the database and shared across all hosts.
- Schema (conceptual): a pool table, a pool-topic table (topic, explanation, column, position), a game table (pool, status, host link), and history tables for draws, claims and winners.

### Real-time contract

- The server broadcasts to every player in a game: each draw, each prize awarded and its winner, each change to the lobby, and the game status.
- The server sends a rejected claim only to the claimant. Ticks and claims are sent from clients as commands to the Game Engine.
- Message schemas are defined with Pydantic and generated into TypeScript types from the OpenAPI schema.

## Testing Decisions

### What makes a good test

Tests check behaviour through the Game Engine's public commands and queries. They don't assert on internal state, storage layout or message formatting. A good test starts from a game in a known state, runs commands with a controlled random source and clock, and asserts on what the game allows, what it rejects and what it reports.

### Seams

- **Primary seam: the Game Engine's command and query interface.** Almost all tests use it. It has no networking or database code in its path, so tests run fast and without setup.
- **Injected randomness and time.** The random source and clock are injected at construction, so tests can fix draw order and settlement timing. This is a new seam, but it sits at the same point as the engine itself, so it adds no new layer.
- **A thin transport test.** One integration test per message type checks that the Realtime Adapter turns a socket event into the matching engine command and broadcasts the result. It doesn't test rules.

### Modules to test

- **Game Engine**: every rule in the Pool, Ticket, Draw, Tick, Claim and Lobby sections above.
- **Ticket Builder**: the ticket invariants, over many generated tickets. Test that every ticket meets them, that no two tickets in a game are identical, and that the column rules hold.
- **Prize Evaluator**: each of the six prize patterns, with positive and negative cases. Four corners gets its own cases for tickets where the top and bottom lines start or end in different columns.
- **Pool Library**: validation of 90 distinct topics, the explanation requirement, the read-only default and the lock on first draw.
- **History Store**: a finished game's draws, claims and winners round-trip correctly.
- **Realtime Adapter**: the transport test described above.

### Specific cases the engine tests must cover

- Joining is rejected after the game starts and after the first draw.
- Joining is rejected at the 201st player.
- Rejoining with the same name restores the ticket and ticks.
- A tick on an undrawn topic is rejected and leaves the state unchanged.
- An invalid claim is rejected and leaves the state unchanged.
- Two valid claims for the same prize within the settlement window both win it.
- A prize already awarded cannot be awarded again.
- A player can win several prizes in one game.
- Draws after the game ends are rejected.
- A pool with 89 or 91 topics, or with duplicate topics, is rejected.

### Prior art

None. The repository has no code yet, so these tests set the pattern for the project.

## Out of Scope

- Accounts, logins or any player identity beyond a display name.
- Auto-marking of ticks.
- Undoing a draw, or any host correction after a draw.
- More than one ticket per player per game.
- Leaderboards, scores across games, or any statistics beyond the stored history.
- Chat between players.
- Payments or real-world prizes.
- Native mobile apps. The web app is responsive but is not packaged as an app.
- Scaling beyond one server process. Moving game state out of memory is a future change, tracked by ADR 0001.
- Moderation, reporting or abuse controls.
- Localisation.
- Analytics.

## Further Notes

### Assumptions to check

These decisions were not explicitly settled in the design session. They are the most likely to need a second look:

1. **Host access.** Players have no accounts, so the host's private link is the only control. If the link leaks, anyone with it can run the game.
2. **Settlement window.** The one-second default for "same moment" claims is a guess. Tune it once there's real use.
3. **Claim validity.** A claim checks that every topic in the pattern is ticked and drawn. Ticked already implies drawn, so the draw check is a safety net.
4. **Unticking.** The spec allows a player to untick before a claim. The design session didn't cover this, and it's easy to remove.
5. **Name uniqueness.** Names are unique within a game, so that rejoining can find the right ticket. Two players can't share a name in the same game.
6. **Column order.** Within a column, the order is the pool's list order. This reconciles the earlier "fixed order" decision with the rule that the app fills columns in list order.
7. **History visibility.** The spec stores finished games but doesn't say who can view them. The default assumption is anyone with the game's identifier.

### Design sources

- Design grilled in the conversation that produced this spec, with the terms recorded in `GLOSSARY.md` at the repository root.
- Architecture recorded in `docs/adr/0001-fastapi-vue-with-in-memory-game-state.md`.
- Issue tracker and triage vocabulary configured in `docs/agents/`.
