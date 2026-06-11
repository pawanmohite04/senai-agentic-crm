import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def main():
    client = TestClient(app)
    client.post("/seed/knowledge-base")
    emails = json.loads(Path("email-data-advanced.json").read_text(encoding="utf-8"))
    for item in emails:
        response = client.post("/api/ingest", json=item)
        print(item["message_id"], response.status_code, response.json())


if __name__ == "__main__":
    main()
