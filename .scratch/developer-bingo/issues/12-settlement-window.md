# 12: Settlement window for simultaneous claims

**What to build:** When the first valid claim for a prize arrives, the engine opens a short settlement window. Every valid claim for that prize received in the window wins it together. Draws are held until the window closes.

**Blocked by:** 08 (Claim Early five)

**Status:** ready-for-agent

- [ ] The first valid claim for a prize opens the settlement window
- [ ] Valid claims for the same prize within the window all win together
- [ ] Draws are held until the window closes
- [ ] The window length defaults to one second and is configurable
- [ ] Claims are judged against the draws at window close
