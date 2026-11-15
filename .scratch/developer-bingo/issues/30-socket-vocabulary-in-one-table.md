# 30: One table for the socket vocabulary

**What to build:** The socket messages are declared in three places that nothing ties together:

- the `ClientEvent` and `ServerEvent` enums (`wire.py:33-62`)
- the hand-kept `SOCKET_MODELS` list (`wire.py:364`), which `app.py` merges into the OpenAPI schema
- the emit sites in `realtime.py`, which pick the event and build the model

A message that is emitted but missing from `SOCKET_MODELS` silently drops out of the OpenAPI schema. `npm run gen:api` would then produce no frontend type for it, and nothing would fail. The lists match today. This is drift risk, not a live bug.

**Blocked by:** none

**Status:** done

- [x] `tests/test_socket_vocabulary.py` fails when a `ServerEvent` has no entry in `SERVER_MESSAGES`, and when a message an event carries is missing from `SOCKET_MODELS`. The second check runs one way only: client and acknowledgement models are never reached from an event, so a check the other way would fail on them by design
- [x] `wire.py` has one table, `SERVER_MESSAGES`, mapping each `ServerEvent` to its model. `SOCKET_MODELS` is built from it, and `RealtimeAdapter._emit` raises a `TypeError` for a message of the wrong model. The raise sits outside the try block, so it is not logged and swallowed like a failed send
- [x] Regenerating the OpenAPI file and `schema.d.ts` produces byte-identical output, so the wire contract is unchanged
- [x] `ClientEvent` is untouched

## Notes

- Found in the architecture review of 2026-11-13 (candidate 5).
- `DrawAnnouncement` is not listed in `SOCKET_MODELS` directly. It reaches the schema through `GameSnapshot`. The guard test must allow for that, or list it explicitly.
