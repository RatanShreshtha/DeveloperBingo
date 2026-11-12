# 23: The settlement window lives in the engine

**What to build:** One module owns the whole settlement window: opening it, closing it on time, judging the claims, awarding the prize, ending the game on a full house, and getting each claimant their result. Today this rule is split four ways:
- `settlement.py` judges the claims.
- `game.py` opens and closes windows and ends the game.
- `realtime.py` owns the clock (`Scheduler`, `window_seconds`), holds each claimant's acknowledgement open (`_held`, `_answer_held`, `_announce`), and restates the end reasons `"full_house"` and `"host"`.
- The client re-sends `claim_prize` after a rejoin to get its answer back.

So every timed window test needs `RealtimeAdapter`, `RecordingBroadcaster` and `ManualScheduler`. The client's re-send has a bug: if the window closes between the rejoin and the re-send, the winner's re-send raises `PrizeAlreadyAwarded` (`settlement.py:79`). That logs a bogus refused claim for the host and shows the player "Someone has already been awarded this prize".

**Blocked by:** 22 (One handle per player)

**Status:** ready-for-agent

### Engine

- [x] `GameRegistry` stays the only interface for claims, ending the game and windows. `ClaimSettlement` stays inside it as an internal seam
- [x] The `GameRegistry` constructor takes the `Scheduler`, `window_seconds` (with `DEFAULT_WINDOW_SECONDS` moved from the adapter) and an `on_outcome` listener
- [x] A claim that opens a window schedules the window's close itself. When the window closes on time, the outcome is passed to `on_outcome`. Closing a window that is no longer open (for example, because the host ended the game first) does nothing
- [x] `claim` and `end` return the same outcome type that timed closes send. An outcome says:
  - every claim decided, for the host;
  - who the prize was awarded to;
  - whether the game ended, and its `EndReason`;
  - each claimant's result;
  - whether any window is still open
- [x] `GameStatus` and `EndReason` are each named once as a type and used everywhere the literals are written out today

### Adapter and wire

- [x] A claim refused at once still gets a `Refusal` ack. A valid claim gets a `ClaimWaiting` ack straight away, then exactly one `claim_settled {prize, accepted, error?}` event, sent to whichever socket holds the player when the window closes
- [x] The player's snapshot adds `decided_claims` (their own slice of the claim log), so a player who was dropped when the window closed learns the result, and why, on rejoin
- [x] One `publish(code, outcome)` turns outcomes into emits, in this order:
  1. `claim_logged` (to the host) for each decided claim
  2. `prize_awarded`
  3. `game_ended`
  4. each `claim_settled`
  5. `window_changed`, only when the window's state changed
- [x] In `publish`, each emit is tried on its own; a failure is logged and the rest still go out
- [x] `_held`, `_answer_held`, `_announce`, the adapter's call to the scheduler, and the restated end-reason strings are deleted
- [x] `ClaimWaiting`, `ClaimSettled` and `decided_claims` are defined in `wire.py`, and the TypeScript types are regenerated from OpenAPI. Old clients are not supported

### Frontend

- [x] `session.ts` marks a claim as waiting on `ClaimWaiting` or on the snapshot's `pending_claims`
- [x] It resolves the claim on `claim_settled` or from the snapshot's `decided_claims`
- [x] The claim re-send in `applyPlayerSnapshot` and `sendClaim` and the `attempts`/`mine` generation counter are deleted

### Tests (replace, don't layer)

- [x] Timed window tests move to `GameRegistry` with a `ManualScheduler` and a recording `on_outcome`. The adapter versions are deleted. This covers `test_settlement_realtime.py`, `test_settlement_resilience.py`, and the window cases in `test_session_recovery.py`
- [x] Direct `ClaimSettlement` tests that the registry tests now duplicate are deleted. Tests remain only for judging edge cases that the registry interface can't easily reach
- [x] The adapter keeps three kinds of test:
  - one test per outcome kind checking the order of emits;
  - one test that a failed emit doesn't stop the others;
  - one end-to-end socket test: claim → `ClaimWaiting` → `claim_settled`
- [x] A test covers the old bug: a rejoin while a claim waits, then the window closes, gives exactly one `claim_settled` and no refused claim in the host's log
- [x] Frontend: the re-send cases in `sessionClaims.test.ts` and `sessionRecovery.test.ts` are replaced by `FakeTransport` tests that emit `claim_settled`, and by snapshot tests with `decided_claims`

## Notes

- The decision is recorded in `docs/adr/0002-claim-results-as-player-events.md`.
- Found during the architecture review of 2026-11-12 (candidate 2).
