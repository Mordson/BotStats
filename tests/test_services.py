import discord
from sqlalchemy import select

from core.models import ActivitySession, User, VoiceSession
from core.services import TrackingService
from tests.conftest import make_activity, make_member, make_role, make_voice_channel, make_voice_state


async def test_ensure_user_creates_new_user(tracking_service: TrackingService, db_session):
    member = make_member(id=1, username="alice#0", display_name="Alice", roles=[make_role(10), make_role(20)])

    await tracking_service.ensure_user(member)
    await db_session.commit()

    user = await db_session.get(User, 1)
    assert user is not None
    assert user.username == "alice#0"
    assert user.display_name == "Alice"
    assert sorted(user.role_ids) == [10, 20]


async def test_ensure_user_updates_existing_user_in_place(tracking_service: TrackingService, db_session):
    member = make_member(id=1, username="alice#0", display_name="Alice", roles=[make_role(10)])
    await tracking_service.ensure_user(member)
    await db_session.commit()

    updated = make_member(id=1, username="alice#1", display_name="Alice Renamed", roles=[make_role(30)])
    await tracking_service.ensure_user(updated)
    await db_session.commit()

    result = await db_session.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 1
    assert users[0].username == "alice#1"
    assert users[0].display_name == "Alice Renamed"
    assert users[0].role_ids == [30]


async def test_voice_join_opens_session(tracking_service: TrackingService, db_session):
    member = make_member(id=1)
    channel = make_voice_channel(id=100, name="General")

    await tracking_service.handle_voice_state_update(
        member, make_voice_state(channel=None), make_voice_state(channel=channel)
    )

    result = await db_session.execute(select(VoiceSession).where(VoiceSession.user_id == 1))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].channel_id == 100
    assert sessions[0].channel_name == "General"
    assert sessions[0].end_time is None


async def test_voice_leave_closes_session(tracking_service: TrackingService, db_session):
    member = make_member(id=1)
    channel = make_voice_channel(id=100, name="General")

    await tracking_service.handle_voice_state_update(
        member, make_voice_state(channel=None), make_voice_state(channel=channel)
    )
    await tracking_service.handle_voice_state_update(
        member, make_voice_state(channel=channel), make_voice_state(channel=None)
    )

    result = await db_session.execute(select(VoiceSession).where(VoiceSession.user_id == 1))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].end_time is not None
    assert sessions[0].duration_seconds is not None
    assert sessions[0].duration_seconds >= 0


async def test_voice_channel_switch_closes_old_and_opens_new(tracking_service: TrackingService, db_session):
    member = make_member(id=1)
    channel_a = make_voice_channel(id=100, name="General")
    channel_b = make_voice_channel(id=200, name="Gaming")

    await tracking_service.handle_voice_state_update(
        member, make_voice_state(channel=None), make_voice_state(channel=channel_a)
    )
    await tracking_service.handle_voice_state_update(
        member, make_voice_state(channel=channel_a), make_voice_state(channel=channel_b)
    )

    result = await db_session.execute(
        select(VoiceSession).where(VoiceSession.user_id == 1).order_by(VoiceSession.id)
    )
    sessions = result.scalars().all()
    assert len(sessions) == 2
    assert sessions[0].channel_id == 100
    assert sessions[0].end_time is not None
    assert sessions[1].channel_id == 200
    assert sessions[1].end_time is None


async def test_voice_same_channel_is_noop(tracking_service: TrackingService, db_session):
    member = make_member(id=1)
    channel = make_voice_channel(id=100, name="General")

    await tracking_service.handle_voice_state_update(
        member, make_voice_state(channel=None), make_voice_state(channel=channel)
    )
    await tracking_service.handle_voice_state_update(
        member, make_voice_state(channel=channel), make_voice_state(channel=channel)
    )

    result = await db_session.execute(select(VoiceSession).where(VoiceSession.user_id == 1))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].end_time is None


async def test_presence_new_activity_opens_session(tracking_service: TrackingService, db_session):
    before = make_member(id=1, activities=[])
    after = make_member(id=1, activities=[make_activity("Valorant")])

    await tracking_service.handle_presence_update(before, after)

    result = await db_session.execute(select(ActivitySession).where(ActivitySession.user_id == 1))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].activity_name == "Valorant"
    assert sessions[0].activity_type == "playing"
    assert sessions[0].end_time is None


async def test_presence_ended_activity_closes_session(tracking_service: TrackingService, db_session):
    before = make_member(id=1, activities=[])
    playing = make_member(id=1, activities=[make_activity("Valorant")])
    stopped = make_member(id=1, activities=[])

    await tracking_service.handle_presence_update(before, playing)
    await tracking_service.handle_presence_update(playing, stopped)

    result = await db_session.execute(select(ActivitySession).where(ActivitySession.user_id == 1))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].end_time is not None
    assert sessions[0].duration_seconds is not None


async def test_presence_tracks_simultaneous_activities_independently(
    tracking_service: TrackingService, db_session
):
    before = make_member(id=1, activities=[])
    after = make_member(
        id=1,
        activities=[
            make_activity("Valorant", type=discord.ActivityType.playing),
            make_activity("Spotify", type=discord.ActivityType.listening),
        ],
    )

    await tracking_service.handle_presence_update(before, after)

    result = await db_session.execute(select(ActivitySession).where(ActivitySession.user_id == 1))
    sessions = {s.activity_type: s for s in result.scalars().all()}
    assert set(sessions) == {"playing", "listening"}
    assert all(s.end_time is None for s in sessions.values())


async def test_presence_ignores_custom_status(tracking_service: TrackingService, db_session):
    before = make_member(id=1, activities=[])
    after = make_member(
        id=1, activities=[make_activity("focusing", type=discord.ActivityType.custom)]
    )

    await tracking_service.handle_presence_update(before, after)

    result = await db_session.execute(select(ActivitySession).where(ActivitySession.user_id == 1))
    assert result.scalars().all() == []


async def test_presence_normalizes_name_when_matching_open_session(
    tracking_service: TrackingService, db_session
):
    before = make_member(id=1, activities=[])
    started = make_member(id=1, activities=[make_activity("Call of Duty: Black Ops 7")])
    stopped = make_member(id=1, activities=[])

    await tracking_service.handle_presence_update(before, started)
    # Discord reports a differently-punctuated name for the same game on the next tick.
    await tracking_service.handle_presence_update(
        make_member(id=1, activities=[make_activity("Call of Duty® Black Ops 7")]), stopped
    )

    result = await db_session.execute(select(ActivitySession).where(ActivitySession.user_id == 1))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].end_time is not None


async def test_sync_member_activities_opens_in_progress_activity(
    tracking_service: TrackingService, db_session
):
    member = make_member(id=1, activities=[make_activity("Valorant")])

    await tracking_service.sync_member_activities(member)
    await db_session.commit()

    result = await db_session.execute(select(ActivitySession).where(ActivitySession.user_id == 1))
    sessions = result.scalars().all()
    assert len(sessions) == 1
    assert sessions[0].end_time is None


async def test_sync_member_activities_is_idempotent(tracking_service: TrackingService, db_session):
    member = make_member(id=1, activities=[make_activity("Valorant")])

    await tracking_service.sync_member_activities(member)
    await db_session.commit()
    await tracking_service.sync_member_activities(member)
    await db_session.commit()

    result = await db_session.execute(select(ActivitySession).where(ActivitySession.user_id == 1))
    assert len(result.scalars().all()) == 1


async def test_cleanup_open_sessions_closes_everything(tracking_service: TrackingService, db_session):
    member = make_member(id=1)
    channel = make_voice_channel(id=100, name="General")
    await tracking_service.handle_voice_state_update(
        member, make_voice_state(channel=None), make_voice_state(channel=channel)
    )
    await tracking_service.handle_presence_update(
        make_member(id=1, activities=[]), make_member(id=1, activities=[make_activity("Valorant")])
    )

    await tracking_service.cleanup_open_sessions()

    voice_result = await db_session.execute(select(VoiceSession))
    activity_result = await db_session.execute(select(ActivitySession))
    assert all(s.end_time is not None for s in voice_result.scalars().all())
    assert all(s.end_time is not None for s in activity_result.scalars().all())
