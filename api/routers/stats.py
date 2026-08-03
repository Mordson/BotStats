"""API endpoints with aggregate statistics (for the dashboard)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db_session
from api.schemas import GameTimeOut, VoiceTimeOut
from config import settings
from core.repositories import (
    ActivitySessionRepository,
    UserRepository,
    VoiceActiveSessionRepository,
    VoiceSessionRepository,
    _as_aware_utc,
)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/voice-time", response_model=list[VoiceTimeOut])
async def voice_time_leaderboard(
    since: datetime | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[VoiceTimeOut]:
    """
    User leaderboard by total voice time.

    Blends two sources at the point where voice-active tracking began (the
    earliest ever voice_active_sessions row): before that cutoff, no mute/deafen
    data exists, so plain channel-connection time is used (unchanged historical
    behavior); from the cutoff onward, only voice-active time (mic + headphones
    on, not muted/deafened) is counted. If no active-tracking data exists at all
    yet, falls back entirely to plain connection time.
    """
    voice_repo = VoiceSessionRepository(session)
    voice_active_repo = VoiceActiveSessionRepository(session)
    user_repo = UserRepository(session)

    cutoff = await voice_active_repo.get_earliest_start_time()

    totals: dict[int, int] = {}
    if cutoff is None:
        rows = await voice_repo.total_time_by_user(since=since)
    else:
        since_utc = _as_aware_utc(since) if since is not None else None
        cutoff_utc = _as_aware_utc(cutoff)
        legacy_rows = await voice_repo.total_time_by_user(since=since_utc, until=cutoff_utc)
        active_since = max(since_utc, cutoff_utc) if since_utc is not None else cutoff_utc
        active_rows = await voice_active_repo.total_time_by_user(since=active_since)
        rows = legacy_rows + active_rows

    for user_id, seconds in rows:
        totals[user_id] = totals.get(user_id, 0) + seconds

    users_by_id = {user.id: user for user in await user_repo.get_all()}

    result = [
        VoiceTimeOut(
            user_id=user_id,
            display_name=users_by_id[user_id].display_name if user_id in users_by_id else str(user_id),
            total_seconds=seconds,
        )
        for user_id, seconds in totals.items()
    ]
    return sorted(result, key=lambda item: item.total_seconds, reverse=True)


@router.get("/top-games", response_model=list[GameTimeOut])
async def top_games(
    limit: int = 10,
    since: datetime | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[GameTimeOut]:
    """Game leaderboard by total play time of users with visible roles."""
    repo = ActivitySessionRepository(session)
    rows = await repo.top_games(limit=limit, since=since, role_ids=settings.visible_role_ids_list or None)
    return [GameTimeOut(activity_name=name, total_seconds=seconds) for name, seconds in rows]
