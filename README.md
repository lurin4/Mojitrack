# Mojitrack

Mojitrack is a Japanese reading tracker for logging reading sessions, tracking character counts, setting goals, and viewing reading statistics.

Built with FastAPI, SQLite, HTML, CSS, and JavaScript, with optional Jiten integration for Japanese novel metadata.

## Features

- Reading session logging
- Character and reading-time tracking
- Daily, weekly, and monthly goals
- Reading streaks and activity heatmap
- Progress charts and completion estimates
- Jiten novel search
- JSON/CSV import and export
- Public profiles and API tokens

## Tech Stack

- Python
- FastAPI
- SQLite
- SQLAlchemy
- Alembic
- HTML, CSS, JavaScript
- Chart.js
- Docker
- Railway

## Local Setup

```bash
uv sync --python 3.12
uv run alembic upgrade head
uv run python scripts/download_assets.py
uv run uvicorn app.main:app --reload --port 8000
```

Then open:

```text
http://localhost:8000
```

Create a `.env` from `.env.example` before running the app.

## Deployment

The project is deployed using Docker and Railway, with persistent storage for the SQLite database.

Production site:

https://mojitrack.com

## Testing

```bash
uv run pytest -q
uv run ruff check .
```

## Credits

Novel metadata may be sourced from Jiten:

https://jiten.moe/
