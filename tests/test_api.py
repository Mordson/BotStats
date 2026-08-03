from datetime import datetime, timedelta, timezone

from core.repositories import ActivitySessionRepository, UserRepository, VoiceActiveSessionRepository


async def _create_user(db_session, user_id: int, display_name: str) -> None:
    await UserRepository(db_session).get_or_create(user_id, display_name, display_name, [])
    await db_session.commit()


def test_health(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_list_users_serializes_id_as_string(api_client, db_session):
    await _create_user(db_session, user_id=123456789012345678, display_name="Alice")

    response = api_client.get("/users/")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "123456789012345678"
    assert body[0]["display_name"] == "Alice"


async def test_get_user_found(api_client, db_session):
    await _create_user(db_session, user_id=1, display_name="Alice")

    response = api_client.get("/users/1")

    assert response.status_code == 200
    assert response.json()["display_name"] == "Alice"


def test_get_user_not_found(api_client):
    response = api_client.get("/users/999")
    assert response.status_code == 404


async def test_user_games_returns_aggregated_time(api_client, db_session):
    await _create_user(db_session, user_id=1, display_name="Alice")
    activities = ActivitySessionRepository(db_session)
    now = datetime.now(timezone.utc)
    session_obj = await activities.start_session(
        user_id=1, guild_id=1, activity_name="Valorant", activity_type="playing", start_time=now
    )
    await activities.close_session(session_obj, now + timedelta(seconds=30))
    await db_session.commit()

    response = api_client.get("/users/1/games")

    assert response.status_code == 200
    body = response.json()
    assert body == [{"activity_name": "Valorant", "total_seconds": 30}]


async def test_voice_time_leaderboard_sorted_descending(api_client, db_session):
    await _create_user(db_session, user_id=1, display_name="Alice")
    await _create_user(db_session, user_id=2, display_name="Bob")
    voice = VoiceActiveSessionRepository(db_session)
    now = datetime.now(timezone.utc)

    short_session = await voice.start_session(user_id=1, guild_id=1, start_time=now)
    await voice.close_session(short_session, now + timedelta(seconds=10))
    long_session = await voice.start_session(user_id=2, guild_id=1, start_time=now)
    await voice.close_session(long_session, now + timedelta(seconds=100))
    await db_session.commit()

    response = api_client.get("/stats/voice-time")

    assert response.status_code == 200
    body = response.json()
    assert [row["user_id"] for row in body] == ["2", "1"]
    assert body[0]["total_seconds"] == 100


async def test_voice_time_leaderboard_since_filters_older_sessions(api_client, db_session):
    await _create_user(db_session, user_id=1, display_name="Alice")
    voice = VoiceActiveSessionRepository(db_session)
    now = datetime.now(timezone.utc)
    old_session = await voice.start_session(user_id=1, guild_id=1, start_time=now - timedelta(days=2))
    await voice.close_session(old_session, now - timedelta(days=2) + timedelta(seconds=10))
    await db_session.commit()

    response = api_client.get(
        "/stats/voice-time", params={"since": (now - timedelta(hours=1)).isoformat()}
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_top_games_respects_limit(api_client, db_session):
    await _create_user(db_session, user_id=1, display_name="Alice")
    activities = ActivitySessionRepository(db_session)
    now = datetime.now(timezone.utc)
    for i, name in enumerate(["GameA", "GameB", "GameC"]):
        session_obj = await activities.start_session(
            user_id=1, guild_id=1, activity_name=name, activity_type="playing", start_time=now
        )
        await activities.close_session(session_obj, now + timedelta(seconds=10 + i))
    await db_session.commit()

    response = api_client.get("/stats/top-games", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2
