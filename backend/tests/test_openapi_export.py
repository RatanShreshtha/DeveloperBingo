import json
from pathlib import Path

from devbingo_backend.app import create_app

COMMITTED_SCHEMA = Path(__file__).parents[2] / "frontend" / "src" / "api" / "openapi.json"


def test_the_committed_openapi_schema_matches_the_backend():
    """A message changed without running `npm run gen:api` leaves the frontend types stale."""
    current = create_app("postgresql+psycopg://x@127.0.0.1:1/x").openapi()

    assert json.loads(COMMITTED_SCHEMA.read_text()) == current
