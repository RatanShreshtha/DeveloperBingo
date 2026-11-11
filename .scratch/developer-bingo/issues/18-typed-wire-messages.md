# 18: Typed wire messages

**What to build:** Every socket message is defined once, as a Pydantic model in `wire.py`, and generated into TypeScript like the REST models already are. Today only `DrawAnnouncement` is generated, because a REST route returns it. Every other acknowledgement and event is hand-typed in `frontend/src/realtime/socket.ts`. Error codes and prize names are copied by hand on both sides, and handlers read raw dicts, so a missing field crashes with `KeyError`. ADR-0001 says Pydantic validates every message and that types are generated from the OpenAPI schema; this ticket makes the code match.

**Blocked by:** 16 (Bind players to their socket)

**Status:** ready-for-agent

- [ ] `wire.py` holds a model for every incoming payload, every acknowledgement and every event payload
- [ ] The socket-only models appear in the OpenAPI schema: a custom `app.openapi()` adds their JSON schemas to `components.schemas` with Pydantic's `models_json_schema`. `npm run gen:api` is unchanged
- [ ] Every handler parses its payload into its model; a bad or missing field gets `{ok: false, error: "invalid_message"}` and changes nothing
- [ ] Error codes are a `StrEnum` in `wire.py`. Each `GameError` subclass declares its own code, replacing `_ERROR_CODES` and the inline `"already_joined"` and `"unknown_prize"`
- [ ] A test checks that every `GameError` subclass has a code
- [ ] The frontend's error messages are a `Record<ErrorCode, string>`, so a missing message is a type error
- [ ] `Prize` is a generated enum. The prize board is an ordered list of `{prize, awarded_to}`, so the server decides the order and the frontend no longer seeds its own board
- [ ] `prizes.ts` keeps only labels, as `Record<Prize, string>`
- [ ] One `HostLink` wire model replaces `CreatedGame`, `HostLink` and `CreateGameResponse`; `POST /games` returns it, and `HomeView.vue` uses the generated type
- [ ] Socket event names are constants in `wire.py`. The frontend keeps a short hand-written table of event name → generated payload type
- [ ] `socket.ts` has no hand-written message shapes left

## Notes

- Do this before 17, so 17's changes to the claim messages (`awarded_to`, `claim_not_valid`) are made in generated types.
- Generating the event-name table is out of scope: about ten names don't justify a script.
