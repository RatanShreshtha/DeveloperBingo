# 30: One table for the socket vocabulary

**What to build:** The socket messages are declared in three places that nothing ties together:

- the `ClientEvent` and `ServerEvent` enums (`wire.py:33-62`)
- the hand-kept `SOCKET_MODELS` list (`wire.py:364`), which `app.py` merges into the OpenAPI schema
- the emit sites in `realtime.py`, which pick the event and build the model

A message that is emitted but missing from `SOCKET_MODELS` silently drops out of the OpenAPI schema. `npm run gen:api` would then produce no frontend type for it, and nothing would fail. The lists match today. This is drift risk, not a live bug.

**Blocked by:** none

**Status:** needs-triage

- [ ] A test fails when a `ServerEvent` has no model in `SOCKET_MODELS`, and when a `SOCKET_MODELS` entry is not reachable from an event. This is the cheap guard, and it can ship alone
- [ ] Longer term: one table maps each `ServerEvent` to its model, and both the emit helper and the OpenAPI list read from it, so adding a message is a single edit
- [ ] The regenerated `openapi.json` and `schema.d.ts` are unchanged by either change, so the wire contract stays the same
- [ ] Do not change `ClientEvent` handling in this ticket

## Notes

- Found in the architecture review of 2026-11-13 (candidate 5).
- `DrawAnnouncement` is not listed in `SOCKET_MODELS` directly. It reaches the schema through `GameSnapshot`. The guard test must allow for that, or list it explicitly.
