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
├── core/                  # shared layer — models, repositories, services
│   ├── database.py        # SQLAlchemy async engine (PostgreSQL)
│   ├── models.py          # ORM models: User, VoiceSession, ActivitySession
│   ├── repositories.py    # Repository pattern — all database queries
│   └── services.py        # Service layer — tracking business logic
├── bot/                   # Discord bot (discord.py)
│   ├── main.py            # entry point, cog registration
│   └── cogs/
│       ├── voice_tracker.py    # on_voice_state_update → voice time
│       └── presence_tracker.py # on_presence_update → games/activities
└── api/                   # REST API for the dashboard (FastAPI)
    ├── main.py
    ├── schemas.py          # DTOs (Pydantic) — API contract
    └── routers/
        ├── users.py
        └── stats.py
```

### Design patterns

| Pattern | Where | Why |
|---|---|---|
| **Layered architecture** | `core` / `bot` / `api` | Separates tracking, business logic, data access, and API. Bot and API can be deployed and scaled independently. |
| **Repository pattern** | `core/repositories.py` | All SQL query logic in one place. Services and API have no knowledge of how data is stored. |
| **Service layer** | `core/services.py` | `TrackingService` contains the logic for "what happens when a user joins a channel / starts playing" — independent of discord.py and FastAPI. |
| **Cog / Extension pattern** | `bot/cogs/*` | Each tracking type (voice, presence) as a separate, interchangeable bot module. |
| **DTO / Schema validation** | `api/schemas.py` | API returns its own contract (Pydantic), decoupled from ORM models. |
| **Dependency Injection** | `api/deps.py` + `Depends()` | DB session injected into FastAPI endpoints. |

### Data model

- **users** — `id` (Discord snowflake), `username`, `display_name`, `first_seen`
- **voice_sessions** — voice channel session: `user_id`, `channel_id`, `channel_name`, `start_time`, `end_time`, `duration_seconds`
- **activity_sessions** — activity session (game/streaming/Spotify): `user_id`, `activity_name`, `activity_type`, `start_time`, `end_time`, `duration_seconds`

Duration (`duration_seconds`) is calculated at the moment of **session close** (when the user leaves a channel or changes activity). This allows the dashboard to simply sum `duration_seconds` without any live calculations.

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

# in a second terminal — API for the dashboard
uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`, Swagger docs at `http://localhost:8000/docs`.

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

This starts PostgreSQL, the bot, the API (port `8000`), and the dashboard (port `8501`).

## API endpoints (for the dashboard)

- `GET /users/` — list of users
- `GET /users/{user_id}` — single user data
- `GET /users/{user_id}/games` — per-game playtime for a user
- `GET /stats/voice-time` — user leaderboard by voice channel time
- `GET /stats/top-games` — game leaderboard by total playtime (`limit` query param)

All times are returned in **seconds** (`total_seconds`) — conversion to hours/days is left to the frontend.


