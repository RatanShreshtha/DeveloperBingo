# 19: Frontend game session

**What to build:** One game-session store on the frontend that loads a full snapshot of the game, applies events as they arrive, and recovers after a reconnect or a page reload. Today `socket.ts` is eleven pass-through functions. Views piece together state from a socket acknowledgement plus `GET /games/{code}/draws`, and "started" is guessed from whether any draws exist. So a player who rejoins between the start and the first draw sees "Waiting…", and the host sees "Start game" again.

**Blocked by:** 17 (Deepen claims and engine outcomes), 20 (Pool per game)

**Status:** ready-for-agent

### Snapshot

- [x] `join_game` and `watch_lobby` return one game snapshot: game status, players, draws and the prize board. A player's snapshot adds their Ticket and ticks. The host's snapshot adds the game's Pool Columns
- [x] `HostView` shows the Pool Columns from the snapshot and stops calling `/pools/default`
- [x] `GET /games/{code}/draws` and `GET /games/{code}/lobby` are removed

### Transport seam

- [x] A tiny transport interface: send a command and await its reply, listen for an event, and get notified on reconnect
- [x] Two adapters: socket.io for the app, and a fake transport for tests
- [x] `socket.ts`'s per-event functions and `testing/socketMock.ts` are deleted
- [x] Tests script the fake server (emit an event, drop, reconnect) and assert on store state, instead of digging handlers out of `mock.calls`

### One store

- [x] One game-session store for both the host and players. Shared state: status, players, draws, prize board. Player-only parts (Ticket, ticks, claim) and host-only commands (start, draw) are separate sections of the same store
- [x] On reconnect, the store rejoins (player) or re-watches (host) and applies the fresh snapshot. This replaces 16's minimal rejoin-on-reconnect

### Reload and the rejoin token

- [x] The first `join_game` returns a rejoin token for that player. The frontend keeps the game code, name and token in `sessionStorage`
- [x] On load, the player view rejoins with what is in `sessionStorage` and shows the snapshot, instead of sending the player back to `/join`
- [x] A rejoin with the right token takes over the name even while the old socket is still connected. The old socket is told it was replaced and leaves the game
- [x] Without the token, the rules are unchanged: a dropped player rejoins by name alone, and a connected name gets `name_taken`
- [x] Backend tests cover takeover with the token, refusal without it, and refusal with a wrong token

## Notes

- The rejoin token closes a race: after a reload, the old socket often hasn't dropped yet, so a rejoin by name alone would be refused.
- Splitting host and player into separate stores was considered and rejected: they share most of the state, and a host-only store would hold little.
- Ticket 13 leaves two gaps for the snapshot to fill. `game_ended` is only broadcast live, so a host or player who reloads after the end sees no ended state (the host even sees "Start game" again): the snapshot must carry the game's status and why it ended. A rejoin after the end is refused with `game_ended`, so a player cannot see the final prize board: the snapshot should let them read it.
- Ticks and unticks are still accepted after the game ends. The spec refuses only draws and claims. Decide whether that should change when 12 adds the untick rule.
- Ticket 12 keeps a claimant's pending state only in the browser, for as long as one `claim_prize` acknowledgement is open. After a reload or reconnect inside a settlement window the claim button comes back enabled and the claim looks lost, although the server still holds it. The snapshot should say which of the player's claims are pending, and the rejoin should reattach them to the held result (a second claim from the same player during one window already gets the same result).
- Ticket 12 refuses draws while a window is open (`settlement_open`). The host's snapshot could say a window is open, so the host sees why a draw was refused.
