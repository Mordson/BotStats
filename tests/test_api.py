from datetime import datetime, timedelta, timezone

from core.repositories import VoiceStateSessionRepository
from tests.factories import activity_session, create_user, voice_session, voice_state_session


def test_health(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_list_users_serializes_id_as_string(api_client, db_session):
    await create_user(db_session, user_id=123456789012345678, display_name="Alice")

    response = api_client.get("/users/")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "123456789012345678"
    assert body[0]["display_name"] == "Alice"


async def test_get_user_found(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")

    response = api_client.get("/users/1")

    assert response.status_code == 200
    assert response.json()["display_name"] == "Alice"


def test_get_user_not_found(api_client):
    response = api_client.get("/users/999")
    assert response.status_code == 404


async def test_user_games_returns_aggregated_time(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    await activity_session(db_session, 1, "Valorant", datetime.now(timezone.utc), seconds=30)
    await db_session.commit()

    response = api_client.get("/users/1/games")

    assert response.status_code == 200
    body = response.json()
    assert body == [{"activity_name": "Valorant", "total_seconds": 30}]


async def test_voice_time_leaderboard_sorted_descending(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    await create_user(db_session, user_id=2, display_name="Bob")
    now = datetime.now(timezone.utc)
    await voice_session(db_session, 1, now, seconds=10)
    await voice_session(db_session, 2, now, seconds=100)
    await db_session.commit()

    response = api_client.get("/stats/voice-time")

    assert response.status_code == 200
    body = response.json()
    assert [row["user_id"] for row in body] == ["2", "1"]
    assert body[0]["total_seconds"] == 100


async def test_voice_time_leaderboard_since_filters_older_sessions(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    now = datetime.now(timezone.utc)
    await voice_session(db_session, 1, now - timedelta(days=2), seconds=10)
    await db_session.commit()

    response = api_client.get(
        "/stats/voice-time", params={"since": (now - timedelta(hours=1)).isoformat()}
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_voice_time_leaderboard_until_filters_newer_sessions(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    now = datetime.now(timezone.utc)
    await voice_session(db_session, 1, now - timedelta(minutes=5), seconds=300)
    await db_session.commit()

    response = api_client.get(
        "/stats/voice-time", params={"until": (now - timedelta(hours=1)).isoformat()}
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_voice_time_leaderboard_since_and_until_select_custom_range(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    now = datetime.now(timezone.utc)
    await voice_session(db_session, 1, now - timedelta(days=5), seconds=42)  # in range
    await voice_session(db_session, 1, now - timedelta(hours=1), seconds=3600)  # out of range
    await db_session.commit()

    response = api_client.get(
        "/stats/voice-time",
        params={
            "since": (now - timedelta(days=6)).isoformat(),
            "until": (now - timedelta(days=4)).isoformat(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["total_seconds"] == 42


async def test_voice_channel_leaderboard_sorted_descending(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    await create_user(db_session, user_id=2, display_name="Bob")
    now = datetime.now(timezone.utc)
    await voice_session(db_session, 1, now, seconds=10, channel_id=100, channel_name="General")
    await voice_session(db_session, 2, now, seconds=100, channel_id=200, channel_name="Gaming")
    await db_session.commit()

    response = api_client.get("/stats/voice-channels")

    assert response.status_code == 200
    body = response.json()
    assert [row["channel_name"] for row in body] == ["Gaming", "General"]
    assert body[0]["channel_id"] == "200"
    assert body[0]["total_seconds"] == 100


async def test_voice_channel_leaderboard_merges_same_channel_across_users(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    await create_user(db_session, user_id=2, display_name="Bob")
    now = datetime.now(timezone.utc)
    await voice_session(db_session, 1, now, seconds=30)
    await voice_session(db_session, 2, now, seconds=20)
    await db_session.commit()

    response = api_client.get("/stats/voice-channels")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["total_seconds"] == 50


async def test_top_games_respects_limit(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    now = datetime.now(timezone.utc)
    for i, name in enumerate(["GameA", "GameB", "GameC"]):
        await activity_session(db_session, 1, name, now, seconds=10 + i)
    await db_session.commit()

    response = api_client.get("/stats/top-games", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_earliest_start_time_returns_none_when_no_sessions(db_session):
    repo = VoiceStateSessionRepository(db_session)
    assert await repo.earliest_start_time("unmuted") is None


async def test_earliest_start_time_returns_min_across_all_users(db_session):
    repo = VoiceStateSessionRepository(db_session)
    now = datetime.now(timezone.utc)
    await repo.start_session(user_id=1, guild_id=1, kind="unmuted", start_time=now + timedelta(hours=1))
    await repo.start_session(user_id=2, guild_id=1, kind="unmuted", start_time=now)
    await db_session.commit()

    assert await repo.earliest_start_time("unmuted") == now


async def test_earliest_start_time_is_scoped_to_kind(db_session):
    repo = VoiceStateSessionRepository(db_session)
    now = datetime.now(timezone.utc)
    await repo.start_session(user_id=1, guild_id=1, kind="undeafened", start_time=now)
    await db_session.commit()

    assert await repo.earliest_start_time("unmuted") is None


async def test_engagement_computes_percent_of_voice_time(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    now = datetime.now(timezone.utc)
    await voice_session(db_session, 1, now, seconds=100)
    await voice_state_session(db_session, 1, "unmuted", now, seconds=50)
    await voice_state_session(db_session, 1, "undeafened", now, seconds=25)
    await db_session.commit()

    response = api_client.get("/stats/engagement")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_id"] == "1"
    assert body[0]["voice_seconds"] == 100
    assert body[0]["unmuted_seconds"] == 50
    assert body[0]["undeafened_seconds"] == 25
    assert body[0]["unmuted_percent"] == 50.0
    assert body[0]["undeafened_percent"] == 25.0


async def test_engagement_open_sessions_clamp_to_the_same_instant(api_client, db_session):
    """
    A still-open voice session and a still-open unmuted session (e.g. the user is
    connected and unmuted right now) must clamp to the exact same "now" - otherwise
    two independently-sampled timestamps could push unmuted_percent past 100%.
    """
    await create_user(db_session, user_id=1, display_name="Alice")
    start = datetime.now(timezone.utc) - timedelta(seconds=30)
    await voice_session(db_session, 1, start)
    await voice_state_session(db_session, 1, "unmuted", start)
    await db_session.commit()

    response = api_client.get("/stats/engagement")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["unmuted_percent"] <= 100.0


async def test_engagement_assumes_100_percent_before_any_tracking_exists(api_client, db_session):
    """No VoiceStateSession row of any kind exists yet (feature just deployed, nobody
    has toggled mute/deafen since) - all historical voice time counts as fully engaged."""
    await create_user(db_session, user_id=1, display_name="Alice")
    now = datetime.now(timezone.utc)
    await voice_session(db_session, 1, now - timedelta(seconds=300), seconds=300)
    await db_session.commit()

    response = api_client.get("/stats/engagement")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["unmuted_percent"] == 100.0
    assert body[0]["undeafened_percent"] == 100.0
    assert body[0]["unmuted_estimated"] is True
    assert body[0]["undeafened_estimated"] is True


async def test_engagement_blends_pre_cutoff_assumption_with_real_data_per_dimension(
    api_client, db_session
):
    """Each dimension has its own cutoff (the first-ever tracked session of that kind,
    across all users): voice time before a dimension's cutoff counts as 100% for that
    dimension; real tracked time after it counts for real - and the two cutoffs can differ."""
    await create_user(db_session, user_id=1, display_name="Alice")
    now = datetime.now(timezone.utc)
    await voice_session(db_session, 1, now - timedelta(seconds=300), seconds=300)

    # unmuted cutoff = now-100 (only the last 100s are "real" for this dimension);
    # of those, only 40s were actually unmuted.
    await voice_state_session(db_session, 1, "unmuted", now - timedelta(seconds=100), seconds=40)

    # undeafened cutoff = now-200 (a different, earlier cutoff for this dimension);
    # of those 200s, 150s were actually undeafened.
    await voice_state_session(db_session, 1, "undeafened", now - timedelta(seconds=200), seconds=150)
    await db_session.commit()

    response = api_client.get("/stats/engagement")

    assert response.status_code == 200
    body = response.json()
    # pre-cutoff 200s (assumed 100%) + real 40s = 240/300 = 80.0%
    assert body[0]["unmuted_percent"] == 80.0
    assert body[0]["unmuted_estimated"] is True
    # pre-cutoff 100s (assumed 100%) + real 150s = 250/300 = 83.3%
    assert body[0]["undeafened_percent"] == 83.3
    assert body[0]["undeafened_estimated"] is True


async def test_engagement_not_estimated_when_user_has_no_voice_time_before_cutoff(
    api_client, db_session
):
    await create_user(db_session, user_id=1, display_name="Alice")
    await create_user(db_session, user_id=2, display_name="Bob")
    now = datetime.now(timezone.utc)

    # Establish a global "unmuted" cutoff via another user, long before Bob ever joins.
    await voice_state_session(db_session, 1, "unmuted", now - timedelta(days=1), seconds=10)

    # Bob's entire voice session starts well after that cutoff and is fully unmuted.
    await voice_session(db_session, 2, now - timedelta(seconds=60), seconds=60)
    await voice_state_session(db_session, 2, "unmuted", now - timedelta(seconds=60), seconds=60)
    await db_session.commit()

    response = api_client.get("/stats/engagement")

    assert response.status_code == 200
    bob = next(row for row in response.json() if row["user_id"] == "2")
    assert bob["unmuted_percent"] == 100.0
    assert bob["unmuted_estimated"] is False


async def test_engagement_excludes_users_with_no_voice_time(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")

    response = api_client.get("/stats/engagement")

    assert response.status_code == 200
    assert response.json() == []


async def test_engagement_sorted_by_unmuted_percent_descending(api_client, db_session):
    await create_user(db_session, user_id=1, display_name="Alice")
    await create_user(db_session, user_id=2, display_name="Bob")
    now = datetime.now(timezone.utc)
    for user_id, unmuted_seconds in [(1, 10), (2, 90)]:
        await voice_session(db_session, user_id, now, seconds=100)
        await voice_state_session(db_session, user_id, "unmuted", now, seconds=unmuted_seconds)
    await db_session.commit()

    response = api_client.get("/stats/engagement")

    assert response.status_code == 200
    body = response.json()
    assert [row["user_id"] for row in body] == ["2", "1"]
