# What Every File Does

You do not run each Python file individually. For normal use, you run the
commands in [START_HERE.md](START_HERE.md). Uvicorn loads the backend modules;
your browser loads the frontend files.

There is no Discord implementation in this project. Your original `bot.py`
stays separate and is not imported, copied into the website or executed.
Only its saved-data format is supported by an optional JSON import.

## Documentation and Configuration

| File | Purpose | Do you edit or run it? |
| --- | --- | --- |
| `START_HERE.md` | Beginner setup guide, explaining commands and expected results. | Read it first. |
| `FILES_EXPLAINED.md` | This file-by-file reference. | Read when you want to understand a part. |
| `README.md` | More detailed behavior, API/import formats and deployment guide. | Read for advanced setup or exact rules. |
| `pyproject.toml` | Lists Python libraries, Python version and tool configuration. | uv reads it; edit only when intentionally changing dependencies. |
| `.env.example` | Template showing supported settings. Contains no real secret. | Use it once to create `.env`. |
| `.gitignore` | Keeps secrets, databases and temporary files out of normal Git commits. | Git reads it if you use version control. |
| `.dockerignore` | Excludes your `.env`, local database and caches from Docker builds. | Docker reads it. |
| `alembic.ini` | Tells Alembic where the migration scripts live. | Read automatically by Alembic. |

Files created when **you** set up or use the site:

| File or folder | What it stores |
| --- | --- |
| `.env` | Your actual configuration and private cookie-signing secret. |
| `.venv/` | The project's installed Python environment. |
| `uv.lock` | Exact dependency versions resolved during installation. |
| `data/reading.db` | The real SQLite database containing users and reading records. |
| `data/reading.db-wal` and `-shm` | SQLite's working files while using write-ahead logging. |
| `backups/` | Timestamped full database snapshots you create with the backup script. |
| `static/vendor/` | Downloaded Chart.js/Lucide libraries and their licenses. |

`.env`, `data/`, and `backups/` are personal data, not disposable source files.

## Backend: app/

| File | What it does |
| --- | --- |
| `app/__init__.py` | Marks `app` as a Python package. It has no startup or Discord code. |
| `app/main.py` | Creates FastAPI, adds routes, serves the frontend and applies request-size and browser-origin protections. Uvicorn starts here. |
| `app/config.py` | Reads `.env`, validates the secret/origin and exposes settings to the other modules. |
| `app/db.py` | Opens database connections, configures SQLite and provides a database session for each request. |
| `app/models.py` | Defines the database tables as Python classes. |
| `app/schemas.py` | Defines acceptable request data: fields, types, positive counts, date range and timezone validation. |
| `app/auth.py` | Hashes/verifies passwords, signs cookies, resolves the logged-in user, revokes sessions and throttles login attempts. |
| `app/stats.py` | Calculates totals, streaks, averages, timezones and daily chart/heatmap data. |
| `app/jiten.py` | Calls Jiten's public API, translates results, caches responses and handles timeouts/rate limits. Entirely optional for manual tracking. |
| `app/importer.py` | Validates optional uploaded JSON, selects one source user's data, previews changes and writes the accepted records in a transaction. It never connects to the old bot. |
| `app/counting.py` | The exact character ranges and category calculations from your supplied counter, shared by the CLI and website. Pure standard-library Python. |

`app/models.py` defines these tables:

| Table | Stored information |
| --- | --- |
| `users` | Website usernames, password hashes, timezone, goals and public-profile preference. No Discord login details. |
| `media` | Your library titles, statuses and optional Jiten statistics. |
| `logs` | Characters read, reading date, title ID and optional minutes for each session. |
| `sessions` | Hashed session identifiers and expiry times, so logging out can invalidate a cookie. |
| `api_tokens` | Hashed personal tokens for optional quick-log scripts. |
| `imports` | Fingerprints of applied imports to block a repeat of the same selected data. |

### Request Handlers: app/routes/

A route is the Python function that handles a particular URL. For example,
clicking Save reading sends data to `/api/logs`; its handler saves that record.

| File | Requests it handles |
| --- | --- |
| `routes/__init__.py` | Marks this folder as a Python package. |
| `routes/auth.py` | Register, login, logout, account preferences and personal API tokens. |
| `routes/logs.py` | List, create, edit and delete reading logs, with ownership checks. |
| `routes/media.py` | Library entries, progress estimates, Jiten searches and stats refreshes. |
| `routes/stats.py` | Summary numbers, daily series and per-title cumulative progress. |
| `routes/transfer.py` | Download CSV/JSON, optionally import a JSON file and count pasted text. |

Do not start these modules separately. `app/main.py` loads their routers.

## Frontend: static/

| File | What it does |
| --- | --- |
| `index.html` | Page structure: account form, Overview, Library, History, Settings and dialogs. |
| `style.css` | Colors, spacing, responsive layout and how controls look. |
| `app.js` | Connects buttons/forms to the API, updates the page and draws charts/heatmap. |
| `profile.html` | Structure of the optional public profile page. |
| `profile.js` | Fetches and renders public aggregate stats only when you have opted in. |
| `icon.svg` | Local book icon used by the header and browser tab. |
| `manifest.webmanifest` | Name, icon and launch URL for supporting browsers' home-screen shortcuts. It does not provide offline storage. |
| `vendor/chart.umd.js` | Chart.js, downloaded during setup; draws bar/line charts. |
| `vendor/lucide.js` | Lucide, downloaded during setup; supplies button icons. |
| `vendor/chart.LICENSE.md`, `vendor/lucide.LICENSE` | Licenses retained alongside those downloaded libraries. |

Open the website through Uvicorn. Opening `index.html` directly from Explorer
cannot provide login, database access or API responses.

## Database Migrations: alembic/

| File | What it does |
| --- | --- |
| `alembic/env.py` | Connects Alembic to the configured database and the model definitions. |
| `alembic/versions/0001_initial.py` | Creates the initial tables when you run `alembic upgrade head`. |
| `alembic/script.py.mako` | Template for any new migration file you generate later. Not a script you run directly. |

Changing `models.py` alone does not update an existing database. Future database
structure changes need a new migration. The counter/import changes in this
updated package reuse the current schema.

## Scripts You Can Run Yourself

| File | Example command from the project root | What it does |
| --- | --- | --- |
| `count.py` | `python count.py "C:\path\to\book.txt"` | Prints character statistics for a UTF-8 file using your original rules. Does not write reading logs. |
| `scripts/download_assets.py` | `uv run python scripts/download_assets.py` | Downloads the pinned browser libraries and licenses. |
| `scripts/backup.py` | `uv run python scripts/backup.py` | Takes a consistent SQLite backup and checks its integrity. |
| `scripts/quick_log.py` | `uv run python scripts/quick_log.py 1 1500 --minutes 25` | Sends a reading log to your site, authenticated with `READING_API_TOKEN` from your shell. Optional, no Discord required. |
| `scripts/inspect_bot_data.py` | `python scripts/inspect_bot_data.py "C:\path\to\reading_data.json"` | Optional read-only summary of the old JSON, including source user IDs and totals. Does not import anything. |

For quick logging, `1` is an actual media ID in **your website database**, not
a Discord ID or Jiten ID. `1500` is the character count. Use the site's JSON
export or `GET /api/media` to find the media ID. See README for setting the token.

## Examples and Tests

The files in `examples/` contain dummy data, not your history.

| File | What it demonstrates |
| --- | --- |
| `examples/bot-user-map.json` | The user-ID/`logs`/`daily_goal` structure written by your bot. Optional migration example. |
| `examples/bot-flat.json` | A simpler list-of-logs format the importer also accepts. |
| `tests/conftest.py` | Creates isolated in-memory test databases and test accounts. |
| `tests/test_api.py` | Account isolation, validation, updates/deletion, CSRF, sessions, tokens and exports. |
| `tests/test_stats.py` | Streaks, gaps, leap days, daily totals and averages. |
| `tests/test_jiten.py` | Mocked Jiten search fields, missing titles and rate limits; no network requests. |
| `tests/test_export.py` | Export/restore and explicit source-user selection. |
| `tests/test_bot_import.py` | Your bot's exact JSON format, optional goal transfer, invalid counts and duplicate protection. |
| `tests/test_counting.py` | Your counter's ranges, category quirks, excluded characters, frequencies and printed file report. |

`uv run pytest -q` collects these tests. You do not need to run each one by hand.
The counter tests also work with Python's standard `unittest` runner without
installing the application dependencies.

## Optional Deployment Files

| File | What it does |
| --- | --- |
| `Dockerfile` | Describes a container image: Python, dependencies, browser assets and startup command. |
| `compose.yml` | Runs the app and Caddy together and keeps databases/certificates in persistent volumes. |
| `Caddyfile` | Tells Caddy which domain to serve and where to forward requests; Caddy handles HTTPS. |

You can ignore all three for local use. There is no need to install Docker just
to follow Steps 1-14 in START_HERE.

## What Happens When You Save Reading

1. The form in `index.html` collects the title, date, characters and minutes.
2. `app.js` sends those fields to `POST /api/logs` on your own server.
3. `main.py` applies request protections; `auth.py` checks your session.
4. `schemas.py` validates the values; `routes/logs.py` checks that the title is yours.
5. SQLAlchemy uses the model definitions to write a row into SQLite.
6. The page fetches fresh stats; `stats.py` recomputes them from stored logs.
7. JavaScript updates the counts and charts you see.

No part of this workflow depends on Discord or Jiten.
