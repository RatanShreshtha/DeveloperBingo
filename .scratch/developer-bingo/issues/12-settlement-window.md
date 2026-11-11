# 12: Settlement window for simultaneous claims

**What to build:** When the first valid claim for a prize arrives, the engine opens a short settlement window. Every valid claim for that prize received in the window wins it together. Draws are held until the window closes.

**Blocked by:** 08 (Claim Early five), 17 (Deepen claims and engine outcomes)

**Status:** ready-for-agent

- [ ] The first valid claim for a prize opens the settlement window
- [ ] Valid claims for the same prize within the window all win together
- [ ] Draws are held until the window closes
- [ ] The window length defaults to one second and is configurable
- [ ] Claims are judged against the draws at window close

## Design decisions

Settled in the architecture review of claims (see 17).

- **No clock in the engine.** Closing a window is an engine command. When a claim opens a window, the claim's outcome says so, and the realtime adapter schedules the close after the configured length (one second by default). Tests close the window directly, with no waiting.
- **Draws are held by state, not by time.** The engine refuses a draw while any window is open.
- **The claimant's reply stays open until the window closes.** The adapter holds the `claim_prize` acknowledgement and sends "awarded" or "refused" once the window settles, so the frontend contract doesn't change.
- **Settlement rules:**
  - With no window open for the prize, a claim is judged at once. An invalid claim is refused and opens nothing. A valid one opens the window.
  - A claim that arrives while the window is open is queued and judged at close.
  - Each prize has its own window. Windows for different prizes can be open at the same time.
  - A repeat claim for the same prize by the same player, during one window, gets the same pending result. It is not an error.
  - A claim for a prize that has already been awarded is refused at once.
- **Unticking is refused while the player has a pending claim.** This enforces spec.md's "a player may untick a topic before a claim is made".
