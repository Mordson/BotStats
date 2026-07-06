# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Discord bot that tracks user activity on a private server (voice channel time, and games/streaming/Spotify activity), storing sessions in PostgreSQL, exposed via a FastAPI REST API and visualized in a Streamlit dashboard.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# fill in DISCORD_TOKEN, set DATABASE_URL to a local PostgreSQL instance

python -m bot.main                    # start the bot
uvicorn api.main:app --reload         # in a second terminal — API (localhost:8000, /docs for Swagger)
streamlit run dashboard/app.py        # in a third terminal — dashboard (needs API running; requirements in dashboard/requirements.txt)
```

## Running with Docker Compose

```bash
cp .env.example .env   # fill in DISCORD_TOKEN
docker compose up --build
```

Starts PostgreSQL, bot, API (port 8000), and dashboard (port 8501). When running in Docker, `DATABASE_URL` in `.env` must point to the `postgres` service name, not `localhost`.

There is no test suite, linter, or formatter configured in this repo currently.

## Architecture

Three independent layers sharing one database, all wired together through `config.py` (Pydantic `Settings`, reads `.env`):

- **`core/`** — shared layer, imported by both `bot/` and `api/`:
  - `database.py` — async SQLAlchemy engine/session (`asyncpg`). `init_db()` calls `Base.metadata.create_all`; there are no migrations (e.g. no Alembic) — schema changes just require model changes plus a DB recreate/restart. **Models must be imported (`from core import models`) before `init_db()` runs**, or their tables won't register on `Base.metadata` — see the `# noqa: F401` imports in `bot/main.py` and `api/main.py`.
  - `models.py` — ORM: `User` (Discord snowflake PK), `VoiceSession`, `ActivitySession`.
  - `repositories.py` — **all queries live here**. Neither `services.py` nor `api/` write raw SQL/ORM queries directly.
  - `services.py` — `TrackingService`: the only place that knows how to turn a discord.py event (VoiceState/Presence change) into open/close session calls against the repositories. Cogs stay "dumb" — they just forward events into this service.

- **`bot/`** — discord.py bot. `bot/main.py` is the entry point (intents setup, cog loading, startup cleanup). Cogs in `bot/cogs/` (`voice_tracker.py`, `presence_tracker.py`) each listen for one event type and delegate to `TrackingService`.

- **`api/`** — FastAPI app for the dashboard. `api/schemas.py` defines the Pydantic response DTOs (decoupled from the ORM models — don't return ORM objects directly from routers). `api/deps.py` provides `get_db_session` for `Depends()` injection. Routers: `users.py`, `stats.py`.

- **`dashboard/`** — Streamlit app (`app.py`), a separate deployable that only talks to the API over HTTP (via `API_URL` env var), never touches the database directly.

### Session lifecycle (important invariant)

`duration_seconds` on `VoiceSession`/`ActivitySession` is computed once, at the moment a session is **closed** (user leaves a channel / activity ends) — not live. This lets the dashboard/API just `SUM(duration_seconds)` with no runtime calculation. Two consequences to keep in mind when touching tracking logic:

1. On bot startup, `TrackingService.cleanup_open_sessions()` force-closes any session left open from a previous run/crash (`on_ready` in `bot/main.py`), so a crash never leaves an unbounded-duration session.
2. `on_presence_update` only fires on activity *changes*, so activities already in progress when the bot starts are missed — `TrackingService.sync_member_activities()` is called per-member at startup to open sessions for those, using "now" as the (approximated) start time.

### Activity name normalization

Game/activity names from Discord vary (trademark symbols, `Title: Subtitle` vs `Title Subtitle`). `core/repositories.py::_normalize_activity_name` strips `®™℠` and normalizes `: ` separators so the same game isn't split across multiple leaderboard rows; `_aggregate_by_normalized_name` re-aggregates by the normalized+lowercased key while preserving a canonical display name. Both `TrackingService` (when opening/matching sessions) and `ActivitySessionRepository.top_games` rely on this — if you add a new query that aggregates by activity name, route it through the same helpers rather than aggregating on raw `activity_name`.

### Adding a time-filterable stat (existing pattern)

`top_games` and `voice-time` both take an optional `since: datetime | None` query param, applied in the repository as `WHERE start_time >= since` before aggregation. The dashboard (`dashboard/app.py`) has a shared `TIME_RANGES` dict (label → `timedelta`) rendered as a `st.selectbox`, converted to a UTC `datetime` and passed as an ISO string query param. Follow this same repository → router → dashboard chain for any new time-scoped stat.
