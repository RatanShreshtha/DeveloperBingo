# DeveloperBingo

A tambola-style bingo game for developers. See `GLOSSARY.md` for the domain language and `docs/adr/` for architecture decisions.

## Layout

- `backend/`: FastAPI API with Postgres connectivity (Python, managed with uv)
- `frontend/`: Vue app with Vite and Pinia (TypeScript)

## Running locally

Start Postgres 16 (the default URL expects `bingo:bingo@localhost:5432/devbingo`), then:

```sh
# Backend, from backend/
uv run uvicorn devbingo_backend.app:create_app --factory --reload

# Frontend, from frontend/
npm run dev
```

Override the database with `DATABASE_URL`.

## Tests and checks

The backend tests need Postgres running, as above.

```sh
# Backend, from backend/
uv run ruff check        # lint
uv run ruff format       # format (use --check to only verify)
uv run ty check          # type check
uv run pytest

# Frontend, from frontend/
npm run lint          # ESLint
npm run format        # Prettier (use format:check to only verify)
npm run typecheck     # vue-tsc
npm run test          # Vitest
npm run build
```

CI runs every check above, plus a check that the generated API types are current (see below). To also run the lint and format checks on each commit, install the [pre-commit](https://pre-commit.com) hooks once from the repo root:

```sh
uv tool install pre-commit
pre-commit install
```

## API types

The frontend's TypeScript types come from the backend's OpenAPI schema. After changing an API model, regenerate them from `frontend/`:

```sh
npm run gen:api
```

## Deploying

The `Dockerfile` builds the Vue app and runs the API beside it, so one process serves the page, the API and the socket on one origin. `render.yaml` describes the hosting: a web service and a Postgres database.

To deploy on Render:

1. In the Render dashboard, choose **New > Blueprint** and select this repo. Render reads `render.yaml` and creates the web service and database.
2. Wait for the first build. The health check is `/health`; it reports `"database": "up"` once Postgres is reachable.
3. Open the service's `onrender.com` URL. That is the public address.

Keep these in mind:

- **Run one instance.** Live games live in memory in one process (`docs/adr/0001`), so a second instance would split games between them.
- **Don't use free plans for a live game.** A free web service sleeps when idle and a sleep drops every live game. Free Postgres expires after 30 days. Check current prices on Render's pricing page before you commit.
- **Run the image locally** to check it before deploying: `docker build -t devbingo . && docker run -p 8000:8000 -e DATABASE_URL=... devbingo`, then open `http://localhost:8000`.
