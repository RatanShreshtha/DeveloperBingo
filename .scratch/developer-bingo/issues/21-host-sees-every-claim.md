# 21: Host sees every claim

**What to build:** The engine keeps a log of every claim in a game, whether it was accepted or refused. The host sees it live. spec.md story 9: "As a host, I want to see every claim and whether it was accepted, so that I can follow what's happening." No earlier ticket covers this, and today refused claims are not recorded anywhere.

**Blocked by:** 17 (Deepen claims and engine outcomes)

**Status:** ready-for-agent

- [x] Every claim is recorded in order: the player, the prize, and whether it was accepted or refused (with the refusal reason)
- [x] The host sees each claim as it happens
- [x] A refused claim is still told only to the claimant among players. The host's view is the only other place it appears
- [x] The host's snapshot on watch (or rejoin) includes the claims so far
- [x] Tests cover an accepted claim, a refused claim, and the host's view after a reconnect

## Notes

- Build on 17's outcome values: the log records what each `claim` returns.
- Once 12 lands, a claim judged at window close is logged when it is settled, not when it arrives.
- 15 (game history) stores this same log when the game ends.
