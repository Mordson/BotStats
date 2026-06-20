# Discord Activity Bot

Bot Discord do analizy aktywności użytkowników na prywatnym serwerze:
- czas spędzony na kanałach głosowych,
- gry/aktywności (np. "Playing Valorant", Spotify, streaming),

oraz REST API udostępniające te dane dashboardowi.

## Architektura

Projekt jest podzielony na trzy niezależne, ale współdzielące jedną bazę danych
warstwy:

```
discord-activity-bot/
├── config.py              # wspólna konfiguracja (Pydantic Settings)
├── core/                   # warstwa wspólna - modele, repozytoria, serwisy
│   ├── database.py         # silnik SQLAlchemy (async, PostgreSQL)
│   ├── models.py            # modele ORM: User, VoiceSession, ActivitySession
│   ├── repositories.py       # Repository pattern - zapytania do bazy
│   └── services.py            # Service layer - logika biznesowa trackingu
├── bot/                    # bot Discord (discord.py)
│   ├── main.py              # punkt wejścia, rejestracja cogów
│   └── cogs/
│       ├── voice_tracker.py    # on_voice_state_update -> czas na voice
│       └── presence_tracker.py # on_presence_update -> gry/aktywności
└── api/                    # REST API dla dashboardu (FastAPI)
    ├── main.py
    ├── schemas.py           # DTO (Pydantic) - kontrakt API
    └── routers/
        ├── users.py
        └── stats.py
```

### Zastosowane wzorce

| Wzorzec | Gdzie | Dlaczego |
|---|---|---|
| **Layered architecture** | `core` / `bot` / `api` | Rozdzielenie trackingu, logiki biznesowej, dostępu do danych i API. Bota i API można uruchamiać/skalować niezależnie. |
| **Repository pattern** | `core/repositories.py` | Cała logika zapytań SQL w jednym miejscu. Serwisy i API nie wiedzą, jak dane są przechowywane. |
| **Service layer** | `core/services.py` | `TrackingService` zawiera logikę "co się dzieje, gdy user wejdzie na kanał / zacznie grać" - niezależnie od discord.py i FastAPI. |
| **Cog / Extension pattern** | `bot/cogs/*` | Każdy typ trackingu (voice, presence) jako osobny, wymienny moduł bota. |
| **DTO / Schema validation** | `api/schemas.py` | API zwraca własny kontrakt (Pydantic), niezależny od modeli ORM. |
| **Dependency Injection** | `api/deps.py` + `Depends()` | Sesja DB wstrzykiwana do endpointów FastAPI. |

### Model danych

- **users** - `id` (Discord snowflake), `username`, `display_name`, `first_seen`
- **voice_sessions** - sesja na kanale głosowym: `user_id`, `channel_id`, `channel_name`, `start_time`, `end_time`, `duration_seconds`
- **activity_sessions** - sesja aktywności (gra/streaming/Spotify): `user_id`, `activity_name`, `activity_type`, `start_time`, `end_time`, `duration_seconds`

Czas trwania (`duration_seconds`) jest liczony w momencie **zamknięcia** sesji
(gdy użytkownik wyjdzie z kanału / zmieni aktywność). Dzięki temu dashboard
może po prostu sumować `duration_seconds` bez liczenia "na żywo".

## Wymagania wstępne (Discord Developer Portal)

W [Discord Developer Portal](https://discord.com/developers/applications) dla
Twojej aplikacji/bota:

1. Zakładka **Bot** -> **Privileged Gateway Intents** -> włącz:
   - **Server Members Intent**
   - **Presence Intent**

   Bez tego `on_voice_state_update` zadziała tylko częściowo, a
   `on_presence_update` nie będzie wywoływany.

2. Zaproś bota na serwer z uprawnieniami minimum: `View Channels`, `Connect`
   (do widzenia kanałów głosowych).

## Uruchomienie lokalnie (bez Dockera)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# wpisz DISCORD_TOKEN, ustaw DATABASE_URL na lokalny PostgreSQL

# uruchom bota
python -m bot.main

# w drugim terminalu - API dla dashboardu
uvicorn api.main:app --reload
```

API będzie dostępne na `http://localhost:8000`, dokumentacja Swagger na
`http://localhost:8000/docs`.

## Uruchomienie z Docker Compose

```bash
cp .env.example .env
# wpisz DISCORD_TOKEN
```

W `.env` dla wersji dockerowej **host bazy danych musi wskazywać na nazwę
serwisu**, nie na `localhost`:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/discord_activity
```

Następnie:

```bash
docker compose up --build
```

To uruchomi: PostgreSQL, bota oraz API (port `8000`).

## Endpointy API (dla dashboardu)

- `GET /users/` - lista użytkowników
- `GET /users/{user_id}` - dane jednego użytkownika
- `GET /users/{user_id}/games` - czas gry użytkownika w poszczególnych grach
- `GET /stats/voice-time` - ranking użytkowników po czasie na kanałach głosowych
- `GET /stats/top-games` - ranking gier po łącznym czasie gry (parametr `limit`)

Wszystkie czasy są zwracane w **sekundach** (`total_seconds`) - konwersję na
godziny/dni najlepiej wykonać na froncie, w zależności od potrzeb dashboardu.

## Rekomendowane kolejne kroki (produkcja)

- **Migracje bazy** - zastąpić `init_db()` (czyli `create_all`) Alembicem,
  żeby bezpiecznie wprowadzać zmiany schematu bez utraty danych.
- **Agregacja** - dla dużych serwerów dodać osobny scheduler (np.
  `APScheduler`), który raz dziennie agreguje `voice_sessions` /
  `activity_sessions` do tabel `daily_stats`, żeby dashboard nie liczył
  sumy z tysięcy wierszy przy każdym odświeżeniu.
- **Autoryzacja API** - przed wystawieniem API publicznie dodać
  uwierzytelnianie (np. API key, OAuth2) i ograniczyć `CORS_ORIGINS` do
  domeny dashboardu.
- **Dashboard** - osobna aplikacja frontendowa (np. Next.js + Recharts),
  konsumująca powyższe endpointy.
