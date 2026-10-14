"""Write the API's OpenAPI schema to web/openapi.json for frontend type generation.

Usage (from the repo root):
    python -m scripts.export_openapi
then, in web/:
    npm run gen:api
"""

import json
import logging
from pathlib import Path

from app.main import app

OUTPUT = Path(__file__).resolve().parent.parent / "web" / "openapi.json"


def main() -> None:
    logging.disable(logging.CRITICAL)
    OUTPUT.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
