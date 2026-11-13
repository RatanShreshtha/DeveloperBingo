"""The one place a domain error becomes an HTTP response.

Routes let these errors out and add no status code of their own, so a pool that is not found is a
404 and a store that cannot be read is a 503 on every route that can meet them.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from devbingo_backend.history import HistoryUnavailable
from devbingo_backend.pool_library import PoolLibraryUnavailable, PoolNotFound

# Each error, with its status and the `detail` the client reads.
RESPONSES: dict[type[Exception], tuple[int, str]] = {
    PoolNotFound: (404, "pool not found"),
    PoolLibraryUnavailable: (503, "pool library unavailable"),
    HistoryUnavailable: (503, "history unavailable"),
}


def register_error_handlers(app: FastAPI) -> None:
    for error, (status, detail) in RESPONSES.items():

        def respond(_request: Request, _error: Exception, status=status, detail=detail) -> JSONResponse:
            return JSONResponse(status_code=status, content={"detail": detail})

        app.add_exception_handler(error, respond)
