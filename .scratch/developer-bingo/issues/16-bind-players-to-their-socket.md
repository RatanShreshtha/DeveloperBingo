# 16: Bind players to their socket

**What to build:** A player's commands act as the player who joined on that socket, not as whatever name the message carries. Today `tick_topic`, `untick_topic` and `claim_prize` build the player from `payload["name"]`, so any socket, even one that never joined, can tick, untick or claim as any player. The frontend also rejoins after a reconnect, so a dropped player gets their place back instead of being refused.

**Blocked by:** none

**Status:** ready-for-agent

- [ ] Tick, untick and claim take the player from the socket's session, not from the message
- [ ] A socket that has not joined is refused with `not_joined`, and nothing changes
- [ ] A socket cannot act as a different player by putting another name in the message
- [ ] When the socket reconnects, the frontend sends `join_game` again with the same code and name, and the player gets back their ticket, ticks and prize board
- [ ] Host commands keep using the host token sent with each message (the token is a secret, so no socket binding is needed)

## Notes

- Do this before 17. Once identity comes from the socket, a player whose socket reconnected would be refused until they rejoin, so the rejoin-on-reconnect fix must ship in the same change.
- Test in `test_realtime.py`: a socket that never joined is refused a claim, and a player cannot claim under another player's name.
- 19 replaces this ticket's minimal rejoin-on-reconnect with a game-session store that reloads the full snapshot.
