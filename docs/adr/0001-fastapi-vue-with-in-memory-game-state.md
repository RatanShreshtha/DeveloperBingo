# FastAPI and Vue, with each game's state held in memory on a single server process

**Status:** accepted

**Context:** DeveloperBingo needs real-time updates for up to 200 players per game, reconnection without losing a ticket, and a central host who controls every draw. We weighed Node.js with Socket.IO, Next.js, Supabase, Firebase, Cloudflare Durable Objects, Colyseus and Phoenix LiveView. **Decision:** we use a FastAPI backend with `python-socketio` for real-time, Postgres for saved pools and game history, and a Vue (Vite and Pinia) frontend with `socket.io-client`. Each game's authoritative state lives in memory on one server process. **Why:** Python suits the ticket and prize rules, FastAPI's Pydantic models validate every message, and Socket.IO supplies rooms and reconnection. A 200-player cap means one process handles many concurrent games, so we didn't need a shared state layer.

**Consequences:** The in-memory state means the server must run as a single worker, and a restart loses any live game unless state is persisted. Scaling out later means moving game state into Redis or the database. Types are shared across the Python and TypeScript sides by generating them from FastAPI's OpenAPI schema, not by a shared language.
