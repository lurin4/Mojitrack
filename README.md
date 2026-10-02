# Reading Site: Manual Setup

This is the source package for a standalone, self-hosted Japanese reading tracker.
**Start with [START_HERE.md](START_HERE.md)** for the beginner walkthrough: each
command is explained, with what you should see before moving on.
See [FILES_EXPLAINED.md](FILES_EXPLAINED.md) for what every supplied file does.

**Discord is not required.** There is no Discord login, token, client library,
bot process or connection. You create a normal website account. Importing old
bot JSON is an optional, one-time file operation; the bot can stay switched off.
You run every installation, migration, test, server and deployment command yourself.
Nothing in this package has been installed, started or deployed for you.

Start with local setup. Docker deployment is a separate, optional step.

## What is included

- FastAPI backend, SQLite database, SQLAlchemy models and an initial Alembic migration.
- Accounts, Argon2 passwords, signed cookies backed by revocable database sessions,
  CSRF protection, account isolation, and registration controls.
- Add/edit/delete reading logs, backdating, optional session minutes.
- Daily/weekly/monthly goals, reading and goal streaks, 365-day activity heatmap,
  stacked 7/30/90-day charts, totals by title, best day and averages.
- Jiten novel search, adding titles, metadata refresh, manual titles and statuses.
- Progress charts, finish estimates and timed-session characters/hour.
- CSV/JSON export, previewable JSON import and consistent SQLite backups.
- Personal API tokens, a quick-log script, optional public aggregate profiles,
  and a web app manifest for browsers that support adding sites to the home screen.
- Docker, Caddy, persistent volumes and tests you can run yourself.

The frontend is newly written because the earlier page was not attached.
It uses local Chart.js and Lucide assets after you run the download step.

## 1. Project Skeleton, Database and Accounts

### Prerequisites

Install Python 3.12 or 3.13 and uv yourself. Python 3.12 is also used in Docker.

- Python: https://www.python.org/downloads/
- uv installation instructions: https://docs.astral.sh/uv/getting-started/installation/

The following local commands are for **Windows PowerShell**. On Linux/macOS,
use the same `uv` commands, replace `Copy-Item` with `cp`, and use your editor
instead of Notepad. Node.js is not needed.

Extract `reading-site-updated.zip` to a folder of your choice. Open PowerShell inside
its `reading-site` folder, the one containing `pyproject.toml`.

Check your tools:

```powershell
python --version
uv --version
```

Install the project's Python dependencies and development tools:

```powershell
uv sync --python 3.12
```

This creates `.venv` and `uv.lock`. Keep `uv.lock` with your project after your
first successful installation so future installs use the same dependency versions.
The delivered package uses bounded dependency ranges; it does not include an
environment-specific, tested lockfile.

Create your configuration:

```powershell
Copy-Item .env.example .env
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
notepad .env
```

Put the generated random value after `SECRET_KEY=`. Keep these local settings:

```dotenv
SECRET_KEY=YOUR_GENERATED_RANDOM_VALUE
DATABASE_URL=sqlite:///./data/reading.db
APP_ORIGIN=http://localhost:8000
COOKIE_SECURE=false
REGISTRATION_MODE=first_user
DOMAIN=reading.example.com
```

Do not use the literal placeholder as your secret. Do not publish `.env`.
`DOMAIN` is ignored by local Uvicorn; it is used for Docker/Caddy deployment.

Create the database tables:

```powershell
uv run alembic upgrade head
uv run alembic current
```

The current migration should be `0001 (head)`. Your database will be at
`data/reading.db`. Run commands from the project root so relative paths resolve
consistently.

Relevant scripts: `app/config.py`, `app/db.py`, `app/models.py`, `app/auth.py`,
`app/routes/auth.py`, and `alembic/versions/0001_initial.py`.

Registration modes:

- `first_user`: lets you create the first account, then closes registration.
- `open`: lets other people register. Use this only when you intend to share the server.
- `closed`: prevents all new registrations.

Restart the server after changing `.env`. Usernames are case-insensitive,
3-40 ASCII letters/digits/underscores. Passwords must be 12-128 characters.
There is no email verification or password-reset email service.

## 2. Logs, Stats and Tests

Run the included tests yourself:

```powershell
uv run pytest -q
uv run ruff check .
```

Tests use a separate in-memory SQLite database and do not change your actual
reading database. They cover account isolation, session revocation, CSRF, log
validation, edit/delete totals, streak grace periods, leap days, import preview,
atomic rejection, duplicate imports, export/restore, token revocation and mocked
Jiten responses. Jiten tests do not make live API requests.

Stats rules:

- A date is a calendar day in the account's configured timezone.
- Future dates are rejected. Backdating is allowed from 1900-01-01 onward.
- Multiple sessions for one title/day are added together.
- A reading streak counts days with any reading. A goal streak uses the current
  daily goal for every historical day.
- If today has not qualified yet, an unbroken streak through yesterday remains
  active. Missing yesterday breaks it unless today starts a new streak.
- Calendar-day average includes zero-reading days from the first log to today.
  Reading-day average includes only days with reading.
- Weekly progress starts on Monday. Monthly progress starts on the first.
- Reading speed uses only sessions with minutes recorded.
- Title finish estimates divide remaining characters by that title's average
  over the last 30 calendar days, including zero-reading days. With no recent
  reading there is no estimate. They assume that pace continues on that title.
- Marking a title finished does not fabricate reading logs or change its counts.

Relevant scripts: `app/routes/logs.py`, `app/routes/stats.py`, `app/stats.py`,
`tests/`.

## 3. Frontend and Local Launch

Download the pinned browser libraries once:

```powershell
uv run python scripts/download_assets.py
```

This downloads Chart.js 4.4.8, Lucide 0.468.0 and their licenses into
`static/vendor/`. Browsers then load them from your server, not a CDN.
The initial download requires internet access. You can inspect its fixed URLs
in the script before running it. Without this step, charts/icons will be absent.

Start the app:

```powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open **http://localhost:8000** in your browser. Use exactly that address so it
matches `APP_ORIGIN`. Create your account, add a title, then log some reading.
Stop the local server with Ctrl+C.

The API reference is **http://localhost:8000/docs**. API writes authenticated by
cookies require `X-Reading-Site: 1`; Swagger's default Try It Out does not add
that header. Use the site UI or a personal Bearer token for writes. In scripted
calls you can explicitly supply the header along with the cookie.

If port 8000 is occupied, change `APP_ORIGIN` to `http://localhost:8001` and
launch with `--port 8001`.

Relevant scripts: `static/index.html`, `static/app.js`, `static/style.css`,
`static/profile.html`, `static/profile.js`, `app/main.py`.

## 4. Jiten Search and Library

In Library, search for a novel by Japanese, English or romaji title. Add a
result to your library, then use its refresh icon when you want updated stats.
Manual Add title works without Jiten and without an internet connection.
The search is filtered to Jiten's Novel category, not visual novels or web novels.

The adapter uses these published contracts:

- Search: `/api/media-deck/get-media-decks` with `titleFilter`, `mediaType=4`,
  and `offset` in multiples of 50. Results are expected in `data`.
- Detail: `/api/media-deck/{id}/detail`, with the title under `data.mainDeck`.
- Metadata: `deckId`, `originalTitle`, `characterCount`, `difficultyRaw`
  (falling back to `difficulty`), `uniqueWordCount`, `uniqueKanjiCount`.

Calls are made server-side, cached for 24 hours, paced to at most two upstream
requests per second per process, and made only in response to a user action.
Refresh bypasses the cached entry. A 429 is checked before JSON parsing and its
Retry-After cooldown is respected; the user can retry after that delay.

No Jiten API key is needed for these public endpoints. The public guide and
published source were inspected when this package was written, but a live
search/detail round trip was **not** executed. Upstream contracts can change;
edit `app/jiten.py` if needed. No bulk database mirroring is included.

Sources:

- https://jiten.moe/guides/using-the-api
- https://api.jiten.moe/
- https://github.com/Sirush/Jiten/blob/master/Jiten.Api/Controllers/MediaDeckController.cs
- https://github.com/Sirush/Jiten/blob/master/Jiten.Core/Data/MediaType.cs

The footer and JSON exports attribute Jiten's derived statistics under
CC BY-SA 4.0. Keep that attribution when sharing those statistics.

## 5. Optional Old-Data Import and Export

Skip import completely when starting fresh. Adding titles and reading logs
manually does not depend on any external account or service.

The importer matches the structure written by your supplied `bot.py`: an object
keyed by source user ID, each containing `logs` and `daily_goal`. The actual
`reading_data.json` was not provided or examined, so individual records have not
been checked. The optional inspector summarizes that file without changing it:

```powershell
uv run python scripts/inspect_bot_data.py "C:\Users\glcwf\Documents\Discord_bots\tracker_bot\reading_data.json"
```

That is the expected location only if your bot was launched from its own folder.
`DATA_FILE` in the bot is relative to its working directory. If the file is
elsewhere, use its actual path. The website never runs or imports `bot.py`, and
the inspector never contacts Discord. It simply reads JSON on disk.

Supported input shapes:

1. A list of `{ "title": "...", "date": "YYYY-MM-DD", "chars": 123 }` rows.
2. An object with a `logs` list containing those rows.
3. A top-level object keyed by source user ID, with each value being one of the
   above shapes. Enter that source ID in the import form to select one user.
4. This app's own `reading-site-v1` JSON export, including its media snapshots.

For bot rows, `media` can replace `title`, and `characters` can replace `chars`.
Optional fields are `minutes` and `media_type` (`novel`, `visual_novel`, `manga`,
or `other`). Unknown row fields are rejected. Dates must be date-only strings,
not Unix timestamps. The bot's accepted non-zero-padded dates such as
`2024-1-2` are normalized to `2024-01-02`. Stored title spelling and counts are
retained; the importer does not apply title casing again.

In Settings, choose your JSON file, enter the source user ID printed by the
inspector, and choose whether to import the saved daily goal. Click Preview
import and check the log count, title count, character total and goal change.
Then click Import records. The preview does not write anything. Applying an
import, including a goal change, is one database transaction.

Weekly and monthly website goals are independent and are not overwritten by the
import. Set them yourself afterward (for example, daily goal times 7 and 30).
The original bot's weekly/monthly reports cover rolling 7/30-day windows; the
website's goal totals cover the calendar week/month. Its 7/30-day charts still
show the rolling periods. These numbers can differ without any missing records.

The original bot accepts zero or negative character entries and invalid daily
goals. This website requires positive reading counts. An invalid log rejects
the import and identifies its row; nothing is silently discarded or changed.
If a saved goal is invalid, uncheck goal import to retain your website goal.
Review any problematic log in a separate copy of the JSON, retaining the
untouched original. Negative adjustment logs need a deliberate conversion;
simply deleting them can change totals.

Imported titles start as manual library titles, with no inferred Jiten match,
difficulty or total length. Set the media type and total length in the title's
edit dialog. Searching Jiten adds a new title; it does not automatically attach
metadata to an already-imported title.

Limits: 5 MB per request, 10,000 logs and 10,000 titles per import.
Reimporting the same selected user's payload is rejected, even if other users'
records changed in the file. This is a one-time migration, not a live sync.
**Different files with overlapping sessions are not deduplicated**, because two
identical reading sessions may be legitimate. Back up before importing.

CSV exports contain readable log rows. Spreadsheet formula-like titles are
prefixed with an apostrophe. JSON exports contain title metadata and reading
logs, with IDs remapped on import. For restoration, use an empty account to
avoid duplicates; existing Jiten-title conflicts are rejected.

JSON does not include account passwords, preferences, sessions or tokens.
Use a SQLite backup for complete server restoration.

## 6. Docker and Deployment

This section is optional. It runs the service on a Linux VPS with a domain you
control, Docker Engine and Docker Compose installed. You do those steps yourself.
Point your domain's DNS A record at your VPS. Remove or correct any AAAA record
that points elsewhere. Allow incoming TCP 80 and 443; UDP 443 is optional.

Copy the project to your VPS, keeping your `.env` private. Set:

```dotenv
SECRET_KEY=YOUR_GENERATED_RANDOM_VALUE
DATABASE_URL=sqlite:////app/data/reading.db
APP_ORIGIN=https://reading.your-domain.com
COOKIE_SECURE=true
REGISTRATION_MODE=first_user
DOMAIN=reading.your-domain.com
```

If you already made an account locally, either import a reading JSON export
into a new server account or transfer a complete SQLite backup. Docker's named
database volume is separate from your local `data/` folder; it starts empty.

From the project directory on the VPS:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 app caddy
```

The image installs dependencies and browser assets, applies migrations on
startup, then runs one Uvicorn worker. Caddy obtains HTTPS certificates.
Only Caddy publishes host ports; the app is on the internal Compose network.
Trusted proxy headers are appropriate for this topology. Do not expose the
app container's port directly with that proxy configuration.

The app runs as UID 10001, not root. Named volumes persist the database and
certificates across container restarts and image rebuilds.

Keep `--workers 1`: Jiten cache/throttling and login-attempt throttling are
in-process. Multiple workers require shared rate-limit/cache storage. The
provided service is aimed at one person or a small private group.

### Backups

Local backup:

```powershell
uv run python scripts/backup.py
```

Docker backup:

```bash
docker compose exec -T app .venv/bin/python scripts/backup.py --database /app/data/reading.db --output /app/backups
```

Use your scheduler to run the relevant command nightly. For example, on a
Linux VPS with the project at `/opt/reading-site`, add this to your crontab:

```cron
0 3 * * * cd /opt/reading-site && /usr/bin/docker compose exec -T app .venv/bin/python scripts/backup.py --database /app/data/reading.db --output /app/backups >> /opt/reading-site/backup.log 2>&1
```

Confirm the Docker executable path with `command -v docker` first. The backup
script prints the resulting file path. Copy a named backup off the server:

```bash
docker compose cp app:/app/backups/reading-YOUR-TIMESTAMP.db ./reading-backup.db
```

It uses SQLite's backup API and checks integrity, so it is safe while the app
is running. Do not merely copy the live `.db` file while WAL writes are active.
Backups contain account hashes and private reading data. Store them privately,
keep off-server copies, and set your own retention policy; this script never
deletes older backups.

### Restore a Local Backup

1. Stop Uvicorn with Ctrl+C.
2. Rename the entire `data` folder, including any `-wal` and `-shm` files, to a
   timestamped recovery folder. Do not overwrite or delete it.
3. Create a new `data` folder and put the chosen backup there as `reading.db`.
4. Run `uv run alembic upgrade head`, then start Uvicorn again.

For a Docker restore, stop the app, retain the existing volume as a recovery
copy, and restore the backup into a replacement volume at `/app/data/reading.db`
owned by UID 10001. Keep Caddy stopped until the app is healthy. Never use
`docker compose down -v` as routine shutdown: it deletes named data volumes.

Relevant files: `Dockerfile`, `.dockerignore`, `compose.yml`, `Caddyfile`,
`scripts/backup.py`.

## 7. Optional Extras

### Timed Sessions and Goals

Enter minutes when logging reading. Settings has daily, weekly and monthly goals
and your IANA timezone, such as `Europe/London` or `Asia/Tokyo`.

### Title Charts

Use a title's chart icon to see cumulative characters and its estimated finish
date. The line contains logged dates; it does not manufacture sessions between
them. Historical goal changes and explicit actual finish dates are not stored.

### Character Counter

The Settings counter, `POST /api/count`, and the supplied standalone `count.py`
share the exact Unicode ranges and category rules from your original `count.py`.
The shared code is in `app/counting.py`; no Discord modules are involved.

It includes Japanese punctuation, ideographic spaces, full-width Latin letters
and digits, and half-width kana. Ordinary ASCII letters/digits/spaces are
excluded. Like the original, it does not count every possible Japanese Unicode
character: for example, U+2026 ellipsis and supplementary CJK ideographs outside
its ranges are excluded. The full half-width/full-width block is labeled
"punctuation" in the category breakdown, even for letters/digits. Kana Supplement
characters contribute to the total but not one of the four category subtotals.
These original behaviors are preserved intentionally.

Run the text-file counter independently:

```powershell
python count.py "C:\path\to\novel.txt"
```

This needs only Python. No `.env`, website account, database or running server
is required. It prints the same report categories and top ten characters as
your original counter. The website accepts pasted text and reports its count;
it does not automatically turn the result into a reading log.

### API Token / Quick Log

Create a token in Settings. It is shown once, stored only as a hash on the server,
and grants full access to your account. Creating a new one revokes the old one.
Log out does not revoke API tokens; use Revoke token for that.

In PowerShell:

```powershell
$env:READING_API_TOKEN = 'YOUR_TOKEN_FROM_SETTINGS'
uv run python scripts/quick_log.py 1 1500 --minutes 25 --timezone Europe/London
Remove-Item Env:READING_API_TOKEN
```

Replace `1` with your title's `id`, available in `GET /api/media` or the JSON
export. Add `--url https://reading.your-domain.com` for a hosted instance, and
`--date YYYY-MM-DD` to backdate. The script otherwise uses today's date in
`--timezone`; match this to your account timezone.

### Public Profile and Home-Screen Shortcut

Enable Public profile in Settings to expose only your username, total characters,
reading days and streaks at `/profile/USERNAME`. It is off by default and never
publishes titles or individual sessions. Disable it to make the URL private again.

The manifest provides a home-screen shortcut in supporting browsers. This is
not a full offline PWA: there is no service worker, offline reading cache or
offline write queue, and install prompts depend on the browser.

## File Map

```text
reading-site/
  START_HERE.md FILES_EXPLAINED.md README.md
  count.py
  pyproject.toml
  .env.example
  app/
    main.py config.py db.py models.py schemas.py auth.py
    stats.py jiten.py importer.py counting.py
    routes/auth.py logs.py media.py stats.py transfer.py
  static/
    index.html app.js style.css icon.svg manifest.webmanifest
    profile.html profile.js
    vendor/                  (created by download_assets.py)
  alembic.ini
  alembic/env.py script.py.mako versions/0001_initial.py
  scripts/download_assets.py backup.py quick_log.py inspect_bot_data.py
  tests/
  examples/
  Dockerfile compose.yml Caddyfile
```

## Verification Status

This package is delivered for you to set up manually. Python and JavaScript
syntax checks and the standalone standard-library counter tests have been run.
The new counter's ranges have also been compared with the supplied original.
Dependencies have not been installed, database migrations and the backend
pytest suite have not been run, and the frontend, Docker build, live Jiten
calls and deployment have not been runtime-tested. Regression tests for your
bot's JSON format are included for you to run after installing dependencies.
