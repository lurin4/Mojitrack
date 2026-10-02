"""Consistent SQLite backup, safe while the app is running."""
import argparse
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="data/reading.db")
    parser.add_argument("--output", default="backups")
    args = parser.parse_args()
    source = Path(args.database).resolve()
    if not source.is_file():
        raise SystemExit(f"Database not found: {source}")
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ("reading-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f") + ".db")
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
        check = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise RuntimeError(f"Backup integrity check failed: {check}")
    print(target.resolve())


if __name__ == "__main__":
    main()
