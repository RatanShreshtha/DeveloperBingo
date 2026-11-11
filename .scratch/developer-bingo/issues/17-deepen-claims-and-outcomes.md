# 17: Deepen claims and engine outcomes

**What to build:** Give the Game Engine the shape that tickets 09–13 need. This is a restructure with no new prizes: Early five stays the only prize. Today the prize check (`prizes.satisfies`) only sees a set of topic names, so it cannot express lines or four corners. Awards hold one winner per prize, and the realtime adapter works out what happened by comparing registry state before and after each call. After this ticket, each of 09–12 should be a small change to one module.

**Blocked by:** 16 (Bind players to their socket), 18 (Typed wire messages)

**Status:** ready-for-agent

Build it as four commits, in this order. Every commit keeps all tests passing.

1. **Player record.** Replace `_Game`'s parallel `players`, `display_names`, `tickets`, `ticks` and `connected` with one record per player: display name, Ticket, ticks, connected. A pure refactor.
2. **Ticket layout and Prize Evaluator.**
   - `Ticket` gains `topic_names()`, `line(n)` and `four_corners()`. Four corners are the outermost filled cell on each side of the top line and of the bottom line.
   - A Prize Evaluator inside the engine: given a Ticket and the topics that are both ticked and drawn, it returns the set of prizes the Ticket satisfies. It replaces `satisfies`. `GameRegistry` computes the ticked-and-drawn set.
3. **Outcome values.**
   - `join` returns an outcome saying whether the player joined new or rejoined.
   - `claim` returns an outcome saying the prize was awarded. Refusals stay as `GameError`.
   - The realtime adapter turns outcomes into broadcasts and stops comparing lobby sizes or re-reading the prize board.
4. **Claim settlement.**
   - A Claim settlement module inside the engine holds the awards, with several winners per prize. It calls the Prize Evaluator.
   - On the wire, `prize_awarded` and the prize board carry `awarded_to: list[str]` instead of `winner: str`, and the error `not_won` becomes `claim_not_valid`.
   - Change the models in `wire.py`, regenerate the types with `npm run gen:api`, and update the lobby store and the prize board view to match.

- [x] `_Game` keeps one record per player
- [x] `Ticket` answers `topic_names()`, `line(n)` and `four_corners()`, including tickets whose top and bottom lines start and end in different columns
- [x] The Prize Evaluator decides Early five from a Ticket and the ticked-and-drawn topics; `satisfies` is gone
- [x] `join` and `claim` return outcomes, and the adapter no longer diffs registry state
- [x] Awards hold a list of players per prize; the wire uses `awarded_to` and `claim_not_valid`
- [x] The frontend shows every player a prize was awarded to
- [x] Behaviour for players is otherwise unchanged

## Tests

Replace tests rather than adding new ones on top of the old.

- Prize Evaluator: a table of cases (prize × Ticket), with positive and negative cases. Early five now; 09–11 add rows.
- `Ticket` layout: `line(n)` and `four_corners()`, including the different-columns case.
- `test_claims.py` keeps testing through `GameRegistry`.
- Delete the direct tests of `satisfies`.
- Move the duplicated "topic names on a ticket" and "start and draw everything" setup into shared test helpers.
- Simplify the "a rejoin does not announce" test so it asserts on the join outcome.

## Out of scope

- The settlement window, held draws and the untick rule: see 12.
- Generating the socket types from the backend: see 18, which lands first.
