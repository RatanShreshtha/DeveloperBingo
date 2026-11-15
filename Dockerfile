# One image serves the built Vue app and the API from one origin (see backend/src/devbingo_backend/frontend.py).

# 1. Build the frontend.
FROM node:24-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. The backend, with the built frontend beside it.
FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/backend/.venv/bin:$PATH" \
    FRONTEND_DIR=/app/frontend/dist

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --locked --no-dev

COPY --from=frontend /app/frontend/dist /app/frontend/dist

# One process only: each game's state lives in memory (docs/adr/0001), so a second worker or replica
# would split games between processes. Hosts set PORT; the default is for local runs.
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn devbingo_backend.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
