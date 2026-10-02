"""Print an import summary without editing the bot's JSON or contacting Discord."""
import argparse
import json
from datetime import datetime
from pathlib import Path


def inspect_data(payload):
    if not isinstance(payload, dict) or not payload:
        raise ValueError("Expected a nonempty object keyed by Discord user ID")
    result = []
    for user_id, user_data in payload.items():
        if not isinstance(user_data, dict) or not isinstance(user_data.get("logs"), list):
            raise TypeError(f"User {user_id}: expected an object with a logs list")
        logs = user_data["logs"]
        warnings = []
        titles = set()
        dates = []
        total = 0
        for number, row in enumerate(logs, 1):
            if not isinstance(row, dict):
                warnings.append(f"Row {number}: not an object")
                continue
            title = row.get("media")
            if isinstance(title, str) and title.strip():
                titles.add(title)
            else:
                warnings.append(f"Row {number}: missing or empty media name")
            chars = row.get("chars")
            if type(chars) is int:
                total += chars
            if type(chars) is not int or not 1 <= chars <= 1_000_000_000:
                warnings.append(f"Row {number}: chars must be a positive integer up to 1,000,000,000")
            try:
                day = datetime.strptime(row.get("date", ""), "%Y-%m-%d").date()  # noqa: DTZ007 -- Calendar date only, not a timestamp.
                dates.append(day)
                if day.year < 1900:
                    warnings.append(f"Row {number}: date is before 1900")
            except (ValueError, TypeError):
                warnings.append(f"Row {number}: invalid date")
        goal = user_data.get("daily_goal")
        if goal is not None and (type(goal) is not int or not 1 <= goal <= 1_000_000_000):
            warnings.append("Saved daily goal is invalid for the website")
        result.append({"user_id": user_id, "logs": len(logs), "titles": len(titles), "total_chars": total,
                       "daily_goal": goal, "first_date": min(dates).isoformat() if dates else None,
                       "last_date": max(dates).isoformat() if dates else None, "warnings": warnings})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.file.read_text(encoding="utf-8-sig"))
        summaries = inspect_data(payload)
    except (OSError, ValueError, TypeError) as error:
        raise SystemExit(str(error))
    for summary in summaries:
        print(f"Discord user ID: {summary['user_id']}")
        print(f"  Logs: {summary['logs']}; titles: {summary['titles']}; characters: {summary['total_chars']}")
        print(f"  Daily goal: {summary['daily_goal']}")
        print(f"  Dates: {summary['first_date']} to {summary['last_date']}")
        for warning in summary["warnings"]:
            print(f"  CHECK: {warning}")
        print()
    print("Read-only summary. The website's import preview performs final validation, including future dates.")


if __name__ == "__main__":
    main()
