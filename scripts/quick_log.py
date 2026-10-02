import argparse
import json
import os
from datetime import datetime
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser(description="Log reading with a personal API token")
    parser.add_argument("media_id", type=int)
    parser.add_argument("chars", type=int)
    parser.add_argument("--date", help="YYYY-MM-DD; defaults to today in --timezone")
    parser.add_argument("--timezone", default="Europe/London")
    parser.add_argument("--minutes", type=int)
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    token = os.environ.get("READING_API_TOKEN")
    if not token:
        raise SystemExit("Set READING_API_TOKEN in your shell first")
    day = args.date or datetime.now(ZoneInfo(args.timezone)).date().isoformat()
    body = json.dumps({"media_id": args.media_id, "chars": args.chars, "date": day, "minutes": args.minutes}).encode()
    request = Request(args.url.rstrip("/") + "/api/logs", data=body,
                      headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            print(response.read().decode())
    except HTTPError as error:
        raise SystemExit(f"HTTP {error.code}: {error.read().decode()}")


if __name__ == "__main__":
    main()
