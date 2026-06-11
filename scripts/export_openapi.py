import json
from pathlib import Path

from app.main import app


def main():
    Path("docs/openapi.json").write_text(json.dumps(app.openapi(), indent=2, default=str), encoding="utf-8")
    print("Wrote docs/openapi.json")


if __name__ == "__main__":
    main()
