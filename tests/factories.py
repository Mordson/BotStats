"""Builders for database rows used across the API/genre tests.

Each `*_session` helper records one session through its repository, closing it
after `seconds` (or leaving it open when `seconds` is None). Callers commit.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from core.repositories import (
    ActivitySessionRepository,
    UserRepository,
    VoiceSessionRepository,
    VoiceStateSessionRepository,
)


async def create_user(db_session, user_id: int, display_name: str) -> None:
    await UserRepository(db_session).get_or_create(user_id, display_name, display_name, [])
    await db_session.commit()


async def voice_session(
    db_session,
    user_id: int,
    start: datetime,
    seconds: int | None = None,
    channel_id: int = 100,
    channel_name: str = "General",
) -> None:
    repo = VoiceSessionRepository(db_session)
    session_obj = await repo.start_session(
        user_id=user_id, guild_id=1, channel_id=channel_id, channel_name=channel_name, start_time=start
    )
    if seconds is not None:
        await repo.close_session(session_obj, start + timedelta(seconds=seconds))


async def voice_state_session(
    db_session, user_id: int, kind: str, start: datetime, seconds: int | None = None
) -> None:
    repo = VoiceStateSessionRepository(db_session)
    session_obj = await repo.start_session(user_id=user_id, guild_id=1, kind=kind, start_time=start)
    if seconds is not None:
        await repo.close_session(session_obj, start + timedelta(seconds=seconds))


async def activity_session(
    db_session,
    user_id: int,
    name: str,
    start: datetime,
    seconds: int | None = None,
    activity_type: str = "playing",
) -> None:
    repo = ActivitySessionRepository(db_session)
    session_obj = await repo.start_session(
        user_id=user_id, guild_id=1, activity_name=name, activity_type=activity_type, start_time=start
    )
    if seconds is not None:
        await repo.close_session(session_obj, start + timedelta(seconds=seconds))
