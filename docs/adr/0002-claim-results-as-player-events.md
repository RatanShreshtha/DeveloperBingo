# Claim results arrive as a per-player event, and the engine owns the settlement window's clock

**Status:** accepted

**Context:** A valid claim waits in a settlement window before it is judged. At first the adapter held the claim's socket acknowledgement open until the window closed, and it scheduled the close itself. A held acknowledgement belongs to one socket. When a player reloaded or reconnected while a claim was waiting, the answer had nowhere to go, so the client re-sent the claim to get it back. That re-send could reach the server after the window had closed, and the server then logged a false refusal. With the clock in the adapter, every timed window test had to run through the socket adapter.

**Decision:**
- A valid claim is acknowledged at once with `ClaimWaiting`. Its result arrives later as exactly one `claim_settled` event, sent to whichever socket holds the player when the window closes.
- A player's snapshot carries their decided claims, so a player who was not connected at the close still learns the result.
- The engine (`GameRegistry`) takes the `Scheduler`, the window length and an outcome listener. It closes its own windows and reports what happened as outcomes. The adapter only turns outcomes into emits.

**Why:**
- A result that belongs to the player, not to one socket, survives rejoins without the client retrying, so the false refusal cannot happen.
- With the clock in the engine, the rule "a window always closes" is in one module and can be tested with a fake scheduler, without sockets.

**Consequences:**
- Going back to held acknowledgements would bring back the client-side retry and its race. Don't, even though held acknowledgements look simpler.
- A `claim_settled` emit can fail where an acknowledgement could not, so each emit is tried on its own and the snapshot is the fallback.
- The engine now depends on a `Scheduler` port, with an asyncio adapter in production and a manual one in tests.
- Every other command that announces something (join, start, draw) reports it the same way, in the `Outcome` it returns, and the adapter publishes it through the same path. A failed announcement is logged and the caller still gets their acknowledgement.
