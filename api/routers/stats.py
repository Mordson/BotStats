"""API endpoints with aggregate statistics (for the dashboard)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db_session
from api.schemas import ChannelTimeOut, EngagementOut, GameTimeOut, VoiceTimeOut
from config import settings
from core.repositories import (
    ActivitySessionRepository,
    UserRepository,
    VoiceSessionRepository,
    VoiceStateSessionRepository,
)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/voice-time", response_model=list[VoiceTimeOut])
async def voice_time_leaderboard(
    since: datetime | None = None,
    until: datetime | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[VoiceTimeOut]:
    """User leaderboard by total time spent in voice channels."""
    voice_repo = VoiceSessionRepository(session)
    user_repo = UserRepository(session)

    rows = await voice_repo.total_time_by_user(since=since, until=until)
    users_by_id = {user.id: user for user in await user_repo.get_all()}

    result = [
        VoiceTimeOut(
            user_id=user_id,
            display_name=users_by_id[user_id].display_name if user_id in users_by_id else str(user_id),
            total_seconds=seconds,
        )
        for user_id, seconds in rows
    ]
    return sorted(result, key=lambda item: item.total_seconds, reverse=True)


@router.get("/voice-channels", response_model=list[ChannelTimeOut])
async def voice_channel_leaderboard(
    since: datetime | None = None,
    until: datetime | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[ChannelTimeOut]:
    """Voice channel leaderboard by total time spent, across all users."""
    voice_repo = VoiceSessionRepository(session)
    rows = await voice_repo.total_time_by_channel(since=since, until=until)

    result = [
        ChannelTimeOut(channel_id=channel_id, channel_name=channel_name, total_seconds=seconds)
        for channel_id, channel_name, seconds in rows
    ]
    return sorted(result, key=lambda item: item.total_seconds, reverse=True)


@router.get("/top-games", response_model=list[GameTimeOut])
async def top_games(
    limit: int = 10,
    since: datetime | None = None,
    until: datetime | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[GameTimeOut]:
    """Game leaderboard by total play time of users with visible roles."""
    repo = ActivitySessionRepository(session)
    rows = await repo.top_games(
        limit=limit, since=since, until=until, role_ids=settings.visible_role_ids_list or None
    )
    return [GameTimeOut(activity_name=name, total_seconds=seconds) for name, seconds in rows]


@router.get("/engagement", response_model=list[EngagementOut])
async def engagement_leaderboard(
    since: datetime | None = None,
    until: datetime | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[EngagementOut]:
    """
    Per-user share of voice-channel time spent unmuted / undeafened (self-chosen state
    only - see CONTEXT.md "Engagement"). Users with no voice time in the window are
    excluded (nothing to divide by). Same visibility filter as `/stats/top-games`.
    """
    voice_repo = VoiceSessionRepository(session)
    voice_state_repo = VoiceStateSessionRepository(session)
    user_repo = UserRepository(session)

    # Pin "now" once and pass it into every query below. Each repository's
    # total_time_by_user() otherwise samples its own `now` independently to clamp a
    # still-open session - since these three awaits run one after another, a user
    # currently connected *and* currently unmuted would get their unmuted duration
    # clamped a few ms later than their voice duration, occasionally rounding up to
    # one second more and pushing unmuted_percent just over 100%.
    frozen_now = datetime.now(timezone.utc)
    voice_seconds_by_user = dict(
        await voice_repo.total_time_by_user(since=since, until=until, now=frozen_now)
    )
    unmuted_by_user = dict(
        await voice_state_repo.total_time_by_user(
            "unmuted", since=since, until=until, now=frozen_now
        )
    )
    undeafened_by_user = dict(
        await voice_state_repo.total_time_by_user(
            "undeafened", since=since, until=until, now=frozen_now
        )
    )
    users_by_id = {
        user.id: user for user in await user_repo.get_all(role_ids=settings.visible_role_ids_list or None)
    }

    result = []
    for user_id, voice_seconds in voice_seconds_by_user.items():
        if voice_seconds <= 0 or user_id not in users_by_id:
            continue
        unmuted_seconds = unmuted_by_user.get(user_id, 0)
        undeafened_seconds = undeafened_by_user.get(user_id, 0)
        result.append(
            EngagementOut(
                user_id=user_id,
                display_name=users_by_id[user_id].display_name,
                voice_seconds=voice_seconds,
                unmuted_seconds=unmuted_seconds,
                undeafened_seconds=undeafened_seconds,
                unmuted_percent=round(unmuted_seconds / voice_seconds * 100, 1),
                undeafened_percent=round(undeafened_seconds / voice_seconds * 100, 1),
            )
        )
    return sorted(result, key=lambda item: item.unmuted_percent, reverse=True)
