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

**Claim**:
A player's assertion that they have won a prize, checked against the draws.
_Avoid_: Bingo, call, shout

**Prize**:
An award a claim can win. Each prize is awarded at most once per game.
_Avoid_: Reward, win

**Prize board**:
Every prize in a game, with who each one was awarded to, or that it is still open.
_Avoid_: Leaderboard, scoreboard

**Settlement window**:
The short period, opened by the first valid claim for a prize, during which every valid claim for that prize wins it together. Draws are held until it closes.
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
