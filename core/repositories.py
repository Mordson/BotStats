"""
Repository layer (Repository pattern).

Each repository is responsible for queries related to a single table/model.
This way the service layer (core/services.py) and the API (api/) don't write
SQL/ORM queries themselves - they operate on the repository methods.

If the database changes in the future (e.g. a different table structure,
a different engine), the changes should only affect this file.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ActivitySession, User, VoiceSession


def _normalize_activity_name(name: str) -> str:
    """Strips trademark symbols and normalizes subtitle separators.

    E.g. 'Call of Duty® Black Ops 7' and 'Call of Duty: Black Ops 7'
    are treated as the same game.
    """
    name = re.sub(r'[®™℠]', '', name)
    name = name.replace(': ', ' ')
    return re.sub(r'\s+', ' ', name).strip()


def _aggregate_by_normalized_name(
    rows: list[tuple[str, int]],
    limit: int | None = None,
) -> list[tuple[str, int]]:
    """Merges rows (name, seconds) grouping by normalized name, sorted descending."""
    totals: dict[str, int] = {}
    canonical: dict[str, str] = {}
    for name, seconds in rows:
        key = _normalize_activity_name(name).lower()
        totals[key] = totals.get(key, 0) + (seconds or 0)
        if key not in canonical:
            canonical[key] = _normalize_activity_name(name)
    sorted_games = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    if limit is not None:
        sorted_games = sorted_games[:limit]
    return [(canonical[key], total) for key, total in sorted_games]


def _as_aware_utc(value: datetime) -> datetime:
    """
    Normalizes a datetime to timezone-aware UTC.

    Some databases/dialects (e.g. SQLite) may return naive datetimes
    even if the column is declared as DateTime(timezone=True).
    This function ensures that subtracting two timestamps always
    works, regardless of the backend.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _duration_seconds(start: datetime, end: datetime) -> int:
    return int((_as_aware_utc(end) - _as_aware_utc(start)).total_seconds())


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(
        self, user_id: int, username: str, display_name: str, role_ids: list[int]
    ) -> User:
        """Returns the existing user or creates a new entry and refreshes the profile data."""
        user = await self.session.get(User, user_id)
        if user is None:
            user = User(id=user_id, username=username, display_name=display_name, role_ids=role_ids)
            self.session.add(user)
            await self.session.flush()
        else:
            user.username = username
            user.display_name = display_name
            user.role_ids = role_ids
        return user

    async def get_all(self, role_ids: list[int] | None = None) -> list[User]:
        query = select(User).order_by(User.display_name)
        if role_ids:
            query = query.where(User.role_ids.overlap(role_ids))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)


class VoiceSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start_session(
        self,
        user_id: int,
        guild_id: int,
        channel_id: int,
        channel_name: str,
        start_time: datetime,
    ) -> VoiceSession:
        session_obj = VoiceSession(
            user_id=user_id,
            guild_id=guild_id,
            channel_id=channel_id,
            channel_name=channel_name,
            start_time=start_time,
        )
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def get_open_session(self, user_id: int) -> VoiceSession | None:
        """Finds the user's currently open (unfinished) voice session."""
        result = await self.session.execute(
            select(VoiceSession)
            .where(VoiceSession.user_id == user_id, VoiceSession.end_time.is_(None))
            .order_by(VoiceSession.start_time.desc())
        )
        return result.scalars().first()

    async def close_session(self, session_obj: VoiceSession, end_time: datetime) -> VoiceSession:
        session_obj.end_time = end_time
        session_obj.duration_seconds = _duration_seconds(session_obj.start_time, end_time)
        await self.session.flush()
        return session_obj

    async def close_all_open(self, end_time: datetime) -> None:
        """Closes all 'orphaned' sessions (e.g. after a bot restart)."""
        result = await self.session.execute(
            select(VoiceSession).where(VoiceSession.end_time.is_(None))
        )
        for session_obj in result.scalars().all():
            session_obj.end_time = end_time
            session_obj.duration_seconds = _duration_seconds(session_obj.start_time, end_time)
        await self.session.flush()


    async def total_time_by_user(self, since: datetime | None = None) -> list[tuple[int, int]]:
        """Total time (in seconds) spent in voice channels, grouped by user."""
        conditions = [VoiceSession.duration_seconds.is_not(None)]
        if since is not None:
            conditions.append(VoiceSession.start_time >= since)
        result = await self.session.execute(
            select(VoiceSession.user_id, func.sum(VoiceSession.duration_seconds))
            .where(*conditions)
            .group_by(VoiceSession.user_id)
        )
        return [(user_id, total or 0) for user_id, total in result.all()]


class ActivitySessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start_session(
        self,
        user_id: int,
        guild_id: int,
        activity_name: str,
        activity_type: str,
        start_time: datetime,
    ) -> ActivitySession:
        session_obj = ActivitySession(
            user_id=user_id,
            guild_id=guild_id,
            activity_name=activity_name,
            activity_type=activity_type,
            start_time=start_time,
        )
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def get_open_session(self, user_id: int, activity_name: str) -> ActivitySession | None:
        """
        Finds an open session for the given user activity.

        A user can have several open sessions at once (e.g. playing a game +
        listening to Spotify), so we match by activity name.
        """
        result = await self.session.execute(
            select(ActivitySession).where(
                ActivitySession.user_id == user_id,
                ActivitySession.activity_name == activity_name,
                ActivitySession.end_time.is_(None),
            )
        )
        return result.scalars().first()

    async def close_session(self, session_obj: ActivitySession, end_time: datetime) -> ActivitySession:
        session_obj.end_time = end_time
        session_obj.duration_seconds = _duration_seconds(session_obj.start_time, end_time)
        await self.session.flush()
        return session_obj

    async def close_all_open(self, end_time: datetime) -> None:
        result = await self.session.execute(
            select(ActivitySession).where(ActivitySession.end_time.is_(None))
        )
        for session_obj in result.scalars().all():
            session_obj.end_time = end_time
            session_obj.duration_seconds = _duration_seconds(session_obj.start_time, end_time)
        await self.session.flush()

    async def top_games(
        self,
        limit: int = 10,
        since: datetime | None = None,
        role_ids: list[int] | None = None,
    ) -> list[tuple[str, int]]:
        """Game leaderboard (activity_type == 'playing') by total play time."""
        conditions = [
            ActivitySession.activity_type == "playing",
            ActivitySession.duration_seconds.is_not(None),
        ]
        if since is not None:
            conditions.append(ActivitySession.start_time >= since)
        query = select(ActivitySession.activity_name, ActivitySession.duration_seconds).where(*conditions)
        if role_ids:
            query = query.join(User, User.id == ActivitySession.user_id).where(
                User.role_ids.overlap(role_ids)
            )
        result = await self.session.execute(query)
        return _aggregate_by_normalized_name(result.all(), limit)

    async def total_game_time_by_user(self, user_id: int) -> list[tuple[str, int]]:
        """The given user's play time, grouped by game name."""
        result = await self.session.execute(
            select(ActivitySession.activity_name, ActivitySession.duration_seconds)
            .where(
                ActivitySession.user_id == user_id,
                ActivitySession.activity_type == "playing",
                ActivitySession.duration_seconds.is_not(None),
            )
        )
        return _aggregate_by_normalized_name(result.all())
