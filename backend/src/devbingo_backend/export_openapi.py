import json
import sys
from pathlib import Path

from devbingo_backend.app import create_app


def export_openapi(output_path: Path) -> None:
    """Write the backend's OpenAPI schema to a file for type generation."""
    schema = create_app().openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=2) + "\n")


if __name__ == "__main__":
    export_openapi(Path(sys.argv[1]))
