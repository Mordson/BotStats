# Discord Activity Bot

A Discord bot for tracking user activity on a private server:
- time spent on voice channels,
- games and activities (e.g. "Playing Valorant", Spotify, streaming),

along with a REST API exposing that data to a dashboard.

## Architecture

The project is split into three independent layers that share a single database:

```
discord-activity-bot/
├── config.py              # shared configuration (Pydantic Settings)
├── core/                  # shared layer -models, repositories, services
│   ├── database.py        # SQLAlchemy async engine (PostgreSQL)
│   ├── models.py          # ORM models: User, VoiceSession, ActivitySession
│   ├── repositories.py    # Repository pattern -all database queries
│   └── services.py        # Service layer -tracking business logic
├── bot/                   # Discord bot (discord.py)
│   ├── main.py            # entry point, cog registration
│   └── cogs/
│       ├── voice_tracker.py    # on_voice_state_update → voice time
│       ├── presence_tracker.py # on_presence_update → games/activities
│       └── member_tracker.py   # on_member_update → re-syncs role_ids on role changes
├── api/                   # REST API for the dashboard (FastAPI)
│   ├── main.py
│   ├── schemas.py          # DTOs (Pydantic) -API contract
│   └── routers/
│       ├── users.py
│       └── stats.py
└── dashboard/             # Next.js dashboard (App Router, server-rendered)
    ├── app/
    │   ├── page.tsx            # server component -initial data fetch
    │   └── api/                # route handlers proxying to the FastAPI backend
    ├── components/
    │   ├── Dashboard.tsx        # tabs, time-range picker, client-side refetching
    │   ├── Donut.tsx             # pie chart (voice time / top games / per-user games)
    │   └── RankingList.tsx       # leaderboard list paired with each Donut
    └── lib/
        ├── api.ts               # server-only fetch wrapper (talks to the FastAPI backend)
        └── format.ts             # time-range options, hour/minute formatting, color palette
```

### Dashboard

A Next.js (App Router) app with three tabs, each showing a pie chart (`Donut`) paired with a ranked
list:

- **Czas głosowy** -voice-channel time leaderboard across all tracked users.
- **Top gry** -game leaderboard by total playtime (configurable count via a dropdown).
- **Użytkownik** -per-user breakdown of playtime by game.

A time-range picker (24h / week / month / half-year / year) filters all three tabs via the API's
`since` param (see "API endpoints" below). The dashboard talks to the API only server-side -see
"Running with Docker Compose" for the request-flow details.

### Design patterns

| Pattern | Where | Why |
|---|---|---|
| **Layered architecture** | `core` / `bot` / `api` | Separates tracking, business logic, data access, and API. Bot and API can be deployed and scaled independently. |
| **Repository pattern** | `core/repositories.py` | All SQL query logic in one place. Services and API have no knowledge of how data is stored. |
| **Service layer** | `core/services.py` | `TrackingService` contains the logic for "what happens when a user joins a channel / starts playing" -independent of discord.py and FastAPI. |
| **Cog / Extension pattern** | `bot/cogs/*` | Each tracking type (voice, presence, member/role) as a separate, interchangeable bot module. |
| **DTO / Schema validation** | `api/schemas.py` | API returns its own contract (Pydantic), decoupled from ORM models. |
| **Dependency Injection** | `api/deps.py` + `Depends()` | DB session injected into FastAPI endpoints. |

### Data model

- **users** -`id` (Discord snowflake), `username`, `display_name`, `first_seen`, `role_ids` (current guild role snowflakes, refreshed on every tracked event)
- **voice_sessions** -voice channel session: `user_id`, `channel_id`, `channel_name`, `start_time`, `end_time`, `duration_seconds`
- **activity_sessions** -activity session (game/streaming/Spotify): `user_id`, `activity_name`, `activity_type`, `start_time`, `end_time`, `duration_seconds`

Duration (`duration_seconds`) is calculated at the moment of **session close** (when the user leaves a channel or changes activity). This allows the dashboard to simply sum `duration_seconds` without any live calculations.

There are no migrations (no Alembic) -`init_db()` just calls `Base.metadata.create_all`, which does not
alter already-existing tables. Schema changes are applied by editing `core/models.py` and recreating the
tables (or migrating the columns by hand) against any existing database.

`role_ids` drives `VISIBLE_ROLE_IDS`- based filtering (see below): it's a privacy/visibility feature for the
dashboard's game sections, not an access-control mechanism.

## Prerequisites (Discord Developer Portal)

In the [Discord Developer Portal](https://discord.com/developers/applications) for your application/bot:

1. **Bot** tab → **Privileged Gateway Intents** → enable:
   - **Server Members Intent**
   - **Presence Intent**

   Without these, `on_voice_state_update` will only work partially and `on_presence_update` will never fire.

2. Invite the bot to your server with at minimum: `View Channels`, `Connect` permissions (to see voice channels).

## Running locally (without Docker)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# fill in DISCORD_TOKEN, set DATABASE_URL to your local PostgreSQL

# start the bot
python -m bot.main

# in a second terminal -API for the dashboard
uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`, Swagger docs at `http://localhost:8000/docs`.

To run the dashboard against that local API, in a third terminal:

```bash
cd dashboard
npm install
API_INTERNAL_URL=http://localhost:8000 npm run dev
```

`API_INTERNAL_URL` defaults to `http://api:8000`, which only resolves inside the Docker network -set
it explicitly to your local API URL when running the dashboard outside Docker. It's available at
`http://localhost:3000`.

## Running with Docker Compose

```bash
cp .env.example .env
# fill in DISCORD_TOKEN
```

In `.env` for the Docker version, the **database host must point to the service name**, not `localhost`:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/discord_activity
```

Then:

```bash
docker compose up --build
```

This starts PostgreSQL, the bot, the API (port `8000`), and the dashboard (port `8080`).

The dashboard is a Next.js app (server-rendered React, `dashboard/`) that talks to the API only
server-side (`API_INTERNAL_URL`, defaults to `http://api:8000` inside Docker) -the browser never
calls the API directly, it only ever hits same-origin `/api/...` routes proxied by the dashboard
server.

## API endpoints (for the dashboard)

- `GET /users/` - list of users
- `GET /users/{user_id}` - single user data
- `GET /users/{user_id}/games` - per-game playtime for a user (`since` query param, optional)
- `GET /stats/voice-time` - user leaderboard by voice channel time (`since` query param, optional)
- `GET /stats/top-games` - game leaderboard by total playtime (`limit`, `since` query params)

`since` restricts results to sessions overlapping `[since, now]` -a session that started earlier but
ended (or is still open) after `since` is partially counted rather than dropped. Omitting it returns
all-time totals.

`GET /stats/top-games` additionally filters to users holding one of the configured `VISIBLE_ROLE_IDS`
(server-side, via `config.py`; empty = unfiltered) -a privacy/visibility feature, not access control.

All times are returned in **seconds** (`total_seconds`) -conversion to hours/days is left to the frontend.

## Running tests

```bash
pytest
```

`pytest.ini` sets `pythonpath = .` so `tests/` can import repo-root packages (`core`, `api`, `bot`)
regardless of how pytest is invoked. Run a single test with e.g.:

```bash
pytest tests/test_repositories.py::test_strips_trademark_symbols
```


