# DeveloperBingo

A tambola-style bingo game where players mark developer, computer science and pop-culture topics as a host draws them.

## Language

**Topic**:
A single item (developer concept, CS idea or pop-culture reference) that can appear on a ticket and be drawn by the host.
_Avoid_: Number, item, card

**Pool**:
The set of topics a game draws from. Every ticket is built from the pool. The host can configure a pool per game; a built-in default pool is used otherwise.
_Avoid_: Deck, bag, set

**Draw**:
The host revealing the next topic from the pool. A topic is drawn at most once per game.
_Avoid_: Call, pick, roll

**Ticket**:
A player's board of topics, dealt before the game starts.
_Avoid_: Card, board, sheet

**Host**:
The person who runs the game and performs the draws.
_Avoid_: Caller, admin, moderator

**Player**:
A participant who holds a ticket and ticks off drawn topics.
_Avoid_: User, contestant

**Connected player**:
A player whose socket is live in the game. A player who drops keeps their place and ticks, and can rejoin by name.
_Avoid_: Online player, live player, dropped player (use "dropped" only for a player who is not connected)

**Rejoin token**:
A secret the server gives a player each time they join. Showing it later proves they are the same player, so a reload can take the name back from a connection the server has not yet seen drop. Without it, a connected name is refused.
_Avoid_: Session key, player password

**Game snapshot**:
Everything a client needs to show a game from scratch: its status, why it ended, the players, the draws and the prize board. A player's snapshot adds their Ticket, ticks, pending claims and their own decided claims; the host's adds the Pool Columns, the claim log and whether a settlement window is open.
_Avoid_: Game state dump, sync

**Claim**:
A player's assertion that they have won a prize, checked against the draws.
_Avoid_: Bingo, call, shout

**Decided claim**:
A claim that has been judged, accepted or refused, and written to the Claim log. A claim the game cannot take is decided on arrival; a valid one is decided when its Settlement window closes.
_Avoid_: Resolved claim, processed claim

**Claim log**:
Every decided claim in a game, in the order decided. The host sees it; players see only their own decided claims.
_Avoid_: Claim history, audit log

**Prize**:
An award a claim can win. Each prize is awarded at most once per game.
_Avoid_: Reward, win

**Prize board**:
Every prize in a game, with who each one was awarded to, or that it is still open.
_Avoid_: Leaderboard, scoreboard

**Settlement window**:
The short period, opened by the first valid claim for a prize, during which every valid claim for that prize wins it together. Draws are held until it closes. An ended game has no open window: ending the game settles every window still open.
_Avoid_: Grace period, tie window

**Column**:
One of nine fixed groups that partition the pool. Each ticket holds one to three topics from each column, shown in the column's fixed order.
_Avoid_: Bucket, range

**Line**:
A complete line of five topics on one ticket. The top, middle and bottom lines are three separate prizes.
_Avoid_: Row, strip

**Early five**:
The first player to have any five topics ticked, wherever they sit on the ticket.
_Avoid_: First five, quick five

**Four corners**:
The outermost topic in the top line and in the bottom line, on each side of the ticket.
_Avoid_: Corners

**Full house**:
Every topic on a ticket ticked.
_Avoid_: Block, all cells, house

**Ended game**:
A game that accepts no more draws or claims. It ends when the full house is awarded, or when the host ends it, and it stays ended.
_Avoid_: Finished, closed, over
