"""Serves the built Vue app from the API's own origin, for production.

In development Vite serves the app and proxies the API (see `frontend/vite.config.ts`). In production
one process does both: the built app's files come from `FRONTEND_DIR`, and every other path goes to
the API. The rule for a browser asking for a page is the same as the Vite proxy's: a GET that accepts
HTML under `/games` or `/pools` gets the app, and so does any other path the API does not own.
"""

from pathlib import Path

from fastapi import FastAPI
from starlette.datastructures import Headers
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

# Paths the API or the socket owns. A browser asking for one of these as a page gets the API's answer,
# except under PAGE_PREFIXES, where it gets the app (`/games/:code` is both a page and an API route).
API_PREFIXES = (
    "/health",
    "/games",
    "/pools",
    "/socket.io",
    "/docs",
    "/redoc",
    "/openapi.json",
)
PAGE_PREFIXES = ("/games", "/pools")


def serve_frontend(app: FastAPI, dist: Path) -> None:
    """Serves the built app in `dist` (the output of `npm run build`) from `app`'s origin."""
    index = dist / "index.html"
    if not index.is_file():
        raise RuntimeError(
            f"No built frontend at {index}: run `npm run build` in frontend/"
        )
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon() -> FileResponse:
        return FileResponse(dist / "favicon.svg")

    app.add_middleware(BrowserPages, index=index)


def _under(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes)


class BrowserPages:
    """Answers a browser's page request with the app's `index.html`, and passes everything else on."""

    def __init__(self, app: ASGIApp, index: Path) -> None:
        self.app = app
        self.index = index

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self._wants_page(scope):
            await FileResponse(self.index)(scope, receive, send)
            return
        await self.app(scope, receive, send)

    @staticmethod
    def _wants_page(scope: Scope) -> bool:
        if scope["method"] != "GET":
            return False
        if "text/html" not in Headers(scope=scope).get("accept", ""):
            return False
        path = scope["path"]
        return _under(path, PAGE_PREFIXES) or not _under(path, API_PREFIXES)
