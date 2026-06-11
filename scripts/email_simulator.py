import argparse
import json
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description="Replay SenAI email dataset into the ingestion API.")
    parser.add_argument("--file", default="email-data-advanced.json")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--speed", type=float, default=1.0, help="Emails per second")
    args = parser.parse_args()

    emails = json.loads(Path(args.file).read_text(encoding="utf-8"))
    delay = 1.0 / args.speed if args.speed > 0 else 0
    with httpx.Client(timeout=20) as client:
        for item in emails:
            response = client.post(f"{args.base_url}/api/ingest", json=item)
            print(item["message_id"], response.status_code, response.text)
            if delay:
                time.sleep(delay)


if __name__ == "__main__":
    main()
