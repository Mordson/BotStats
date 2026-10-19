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
│   ├── game_genres.py     # hand-maintained game → genre mapping, per-genre aggregation
│   ├── models.py          # ORM models: User, VoiceSession, ActivitySession
│   ├── repositories.py    # Repository pattern -all database queries
│   └── services.py        # Service layer -tracking business logic
├── bot/                   # Discord bot (discord.py)
│   ├── main.py            # entry point, cog registration
│   ├── tracking.py        # shared cog glue: tracked-member filter, session + error handling
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
    │   ├── DonutRanking.tsx      # a Donut plus its RankingList, as shown in each panel
    │   ├── PanelBody.tsx         # loading / empty / content switch for a panel
    │   └── RankingList.tsx       # leaderboard list paired with each Donut
    └── lib/
        ├── api.ts               # server-only fetch wrapper (talks to the FastAPI backend)
        ├── donutSlices.ts        # which items get their own Donut slice vs. "Inne"
        ├── format.ts             # time-range options, hour/minute formatting, color palette
        ├── proxy.ts              # proxyGet() backing every app/api route handler
        └── rangeData.ts          # the datasets that depend on the selected time range
```

### Dashboard

A Next.js (App Router) app with tabs, each showing a pie chart (`Donut`) paired with a ranked
list:

- **Czas głosowy** -voice-channel time leaderboard across all tracked users.
- **Top gry** -game leaderboard by total playtime (configurable count via a dropdown).
- **Gatunki** -playtime by game genre, with each genre's top 3 games (see "Game genres" below).
- **Użytkownik** -per-user breakdown of playtime by game.

A time-range picker (24h / week / month / half-year / year) filters all tabs via the API's
`since` param (see "API endpoints" below). The dashboard talks to the API only server-side -see
"Dashboard request flow" below.

Each Donut always shows the top 8 items as their own slices. Past that, the next item gets its own
slice (and legend row) while it makes up at least 20% of the remaining "Inne" (other) total, up to
12 slices; if only one item would be left in "Inne", it is shown on its own instead.

### Game genres

Discord doesn't report a game's genre, so `core/game_genres.py` maps each game by hand (keyed by the
lowercased, normalized activity name) to exactly one genre: MMO, FPS, Survival, Symulatory, RPG,
MOBA or Strategie. `IGNORED_GAMES` lists activities left out of genre stats entirely (Roblox, non-game
apps like CurseForge, casual games); they still appear in the per-game stats. Any other game is counted
under "Bez kategorii".

When a new game shows up, check `GET /stats/unclassified-games`, add each listed name to either
`GAME_GENRES` or `IGNORED_GAMES`, then rebuild the API image.

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
alter already-existing tables. Adding a brand-new table in `core/models.py` works as-is; changing an
existing table that holds data (adding/removing/renaming a column, changing a type or constraint)
should go through a proper migration tool such as Alembic rather than hand-edited SQL.

`role_ids` drives `VISIBLE_ROLE_IDS`- based filtering (see below): it's a privacy/visibility feature for the
dashboard's game sections, not an access-control mechanism.

## Prerequisites (Discord Developer Portal)

In the [Discord Developer Portal](https://discord.com/developers/applications) for your application/bot:

1. **Bot** tab → **Privileged Gateway Intents** → enable:
   - **Server Members Intent**
   - **Presence Intent**

   Without these, `on_voice_state_update` will only work partially and `on_presence_update` will never fire.

2. Invite the bot to your server with at minimum: `View Channels`, `Connect` permissions (to see voice channels).

## Running with Docker Compose

The whole project (PostgreSQL, bot, API, dashboard) runs through Docker Compose -don't start the bot,
API or dashboard directly on the host (`python -m bot.main`, `uvicorn`, `npm run dev`), and don't
install Node tooling on the host. A local `.venv` (e.g. for editor tooling) is optional.

```bash
cp .env.example .env
# fill in DISCORD_TOKEN
```

In `.env`, the **database host must point to the `postgres` service name**, not `localhost`:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/discord_activity
```

Then:

```bash
docker compose build            # or: docker compose build <service>
docker compose up -d
docker compose logs -f <service>
```

This starts PostgreSQL, the bot, the API (port `8000`, Swagger docs at `http://localhost:8000/docs`),
and the dashboard (port `8080`).

There is no hot reload: after changing code, rebuild the affected service(s) and run
`docker compose up -d` again.

### Deploying without restarting the bot

Changes that don't touch the bot (`bot/`, or `core/` code the bot uses) can be deployed without
restarting it:

```bash
docker compose up -d --build --no-deps api dashboard
```

Restarting the bot loses voice time: `on_ready` closes all open sessions and re-opens only activity
sessions, so users sitting in voice channels stop being counted until they rejoin. Restart the bot
only when nobody is in a voice channel.

### Dashboard request flow

The dashboard is a Next.js app (server-rendered React, `dashboard/`) that talks to the API only
server-side (`API_INTERNAL_URL`, defaults to `http://api:8000` inside Docker) -the browser never
calls the API directly, it only ever hits same-origin `/api/...` routes proxied by the dashboard
server.

## API endpoints (for the dashboard)

- `GET /users/` - list of users
- `GET /users/{user_id}` - single user data
- `GET /users/{user_id}/games` - per-game playtime for a user
- `GET /stats/voice-time` - user leaderboard by voice channel time
- `GET /stats/voice-channels` - voice channel leaderboard by total time across all users
- `GET /stats/top-games` - game leaderboard by total playtime (plus a `limit` query param)
- `GET /stats/top-genres` - genre leaderboard by total playtime, each with its top 3 games
- `GET /stats/unclassified-games` - games not yet mapped to a genre (nor ignored), by playtime
- `GET /stats/engagement` - per-user share of voice time spent unmuted / undeafened

All `/stats/*` endpoints and `/users/{user_id}/games` take optional `since` and `until` query params
that restrict results to sessions overlapping `[since, until]` (`until` defaults to now) -a session
that started earlier or ended later is partially counted rather than dropped. Omitting both returns
all-time totals.

`GET /stats/top-games`, `GET /stats/top-genres` and `GET /stats/engagement` additionally filter to users holding one of the configured `VISIBLE_ROLE_IDS`
(server-side, via `config.py`; empty = unfiltered) -a privacy/visibility feature, not access control.

All times are returned in **seconds** (`total_seconds`) -conversion to hours/days is left to the frontend.

## Running tests

Tests run inside Docker, like the rest of the project:

```bash
docker compose run --rm api pytest
```

`pytest.ini` sets `pythonpath = .` so `tests/` can import repo-root packages (`core`, `api`, `bot`)
regardless of how pytest is invoked. Run a single test with e.g.:

```bash
docker compose run --rm api pytest tests/test_repositories.py::test_strips_trademark_symbols
```

Dashboard unit tests (Vitest) run in a one-off Node container. The source is mounted read-only and
copied in, so `node_modules` and `package-lock.json` live only inside the throwaway container:

```bash
docker run --rm -v "${PWD}/dashboard:/src:ro" node:22-alpine sh -c "mkdir /app && tar -C /src --exclude=node_modules -cf - . | tar -C /app -xf - && cd /app && npm install --no-package-lock && npm test"
```

## Dependencies

- **Python:** edit `requirements.txt`, then `docker compose build`.
- **JS:** `dashboard/package.json` is the only package file kept in the repo -no `package-lock.json`,
  `yarn.lock`, `pnpm-lock.yaml`, `node_modules/` etc. Change it only from inside a container, always
  with `--no-package-lock` (never `npm ci`, which needs a lockfile), and copy back only `package.json`:

```bash
docker run --rm -v "${PWD}/dashboard:/src" node:22-alpine sh -c "mkdir /app && cp /src/package.json /app && cd /app && npm install --no-package-lock <pkg> && cp package.json /src/"
```

