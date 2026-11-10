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

```sh
# Backend, from backend/
uv run pytest

# Frontend, from frontend/
npm run test        # Vitest
npm run typecheck   # vue-tsc
npm run build
```

## API types

The frontend's TypeScript types come from the backend's OpenAPI schema. After changing an API model, regenerate them from `frontend/`:

```sh
npm run gen:api
```
