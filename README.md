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
