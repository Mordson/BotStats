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
from typing import Iterable, TypeVar

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ActivitySession, User, VoiceSession, VoiceStateSession



# Games Discord sometimes reports under multiple, unrelated-looking names (e.g. a
# short title vs. the full subtitled title) that the generic punctuation/whitespace
# normalization below can't unify on its own. Keys are lowercased, already-normalized
# names; values are the canonical display name to collapse them into.
_ACTIVITY_NAME_ALIASES: dict[str, str] = {
    "s.t.a.l.k.e.r. 2": "S.T.A.L.K.E.R. 2 Heart of Chornobyl",
}


def _normalize_activity_name(name: str) -> str:
    """Strips trademark symbols and normalizes subtitle separators.

    E.g. 'Call of Duty® Black Ops 7' and 'Call of Duty: Black Ops 7'
    are treated as the same game. Also collapses known aliases (see
    `_ACTIVITY_NAME_ALIASES`) for games Discord reports under different names.
    """
    name = re.sub(r'[®™℠]', '', name)
    name = name.replace(': ', ' ')
    name = re.sub(r'\s+', ' ', name).strip()
    return _ACTIVITY_NAME_ALIASES.get(name.lower(), name)


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


_K = TypeVar("_K")


def _window_conditions(
    since: datetime | None,
    until: datetime | None,
    start_col: ColumnElement[datetime],
    end_col: ColumnElement[datetime | None],
) -> list[ColumnElement[bool]]:
    """SQL conditions restricting rows to those that can overlap [since, until].

    A still-open row (`end_col` is NULL) always passes the `until` side - it's
    only excluded there once actually closed after `until`, since open rows are
    clamped to `until` (or now) when summed, not dropped.
    """
    conditions: list[ColumnElement[bool]] = []
    if since is not None:
        conditions.append(or_(end_col.is_(None), end_col >= since))
    if until is not None:
        conditions.append(start_col <= until)
    return conditions


def _sum_overlap_seconds(
    rows: Iterable[tuple[_K, datetime, datetime | None]],
    since: datetime | None,
    until: datetime | None,
    now: datetime,
) -> dict[_K, int]:
    """
    Sums, per key, the seconds of each (start, end) row that overlap [since, until].

    A row that starts before `since` or ends after `until` is only partially
    counted instead of dropped; a still-open row (`end` is None) counts its
    in-progress duration up to `until` (or `now` if `until` is None). `since`
    and `until`, if given, must already be timezone-aware UTC.
    """
    totals: dict[_K, int] = {}
    for key, start, end in rows:
        window_start = _as_aware_utc(start)
        if since is not None and since > window_start:
            window_start = since
        window_end = _as_aware_utc(end) if end is not None else now
        if until is not None and until < window_end:
            window_end = until
        seconds = int((window_end - window_start).total_seconds())
        if seconds > 0:
            totals[key] = totals.get(key, 0) + seconds
    return totals


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


    async def total_time_by_user(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        now: datetime | None = None,
    ) -> list[tuple[int, int]]:
        """
        Total time (in seconds) spent in voice channels, grouped by user.

        Counts only the part of each session that overlaps [since, until] - see
        `_sum_overlap_seconds` for the overlap/clamping semantics. `until` defaults
        to now when omitted. `now` (the instant a still-open session is clamped to)
        defaults to the real current time - pass an explicit, shared value when
        combining totals from several repositories in one request so they all
        clamp open sessions to the same instant instead of drifting apart.
        """
        now = now if now is not None else datetime.now(timezone.utc)
        since_utc = _as_aware_utc(since) if since is not None else None
        until_utc = _as_aware_utc(until) if until is not None else None
        conditions = _window_conditions(
            since_utc, until_utc, VoiceSession.start_time, VoiceSession.end_time
        )
        result = await self.session.execute(
            select(VoiceSession.user_id, VoiceSession.start_time, VoiceSession.end_time).where(*conditions)
        )
        totals = _sum_overlap_seconds(result.all(), since_utc, until_utc, now)
        return list(totals.items())

    async def total_time_by_channel(
        self, since: datetime | None = None, until: datetime | None = None
    ) -> list[tuple[int, str, int]]:
        """
        Total time (in seconds) spent in each voice channel, across all users.

        Same overlap-window semantics as `total_time_by_user`. Rows are grouped by
        `channel_id` (not name) so a channel rename doesn't split its totals across
        two entries; the most recently seen name is used for display.
        """
        now = datetime.now(timezone.utc)
        since_utc = _as_aware_utc(since) if since is not None else None
        until_utc = _as_aware_utc(until) if until is not None else None
        conditions = _window_conditions(
            since_utc, until_utc, VoiceSession.start_time, VoiceSession.end_time
        )
        result = await self.session.execute(
            select(
                VoiceSession.channel_id,
                VoiceSession.channel_name,
                VoiceSession.start_time,
                VoiceSession.end_time,
            )
            .where(*conditions)
            .order_by(VoiceSession.start_time)
        )
        rows = result.all()
        totals = _sum_overlap_seconds(
            ((channel_id, start_time, end_time) for channel_id, _, start_time, end_time in rows),
            since_utc,
            until_utc,
            now,
        )
        names: dict[int, str] = {}
        for channel_id, channel_name, _, _ in rows:
            if channel_id in totals:
                names[channel_id] = channel_name  # rows are ordered by start_time, so this keeps the latest name
        return [(channel_id, names[channel_id], total) for channel_id, total in totals.items()]


class VoiceStateSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start_session(
        self,
        user_id: int,
        guild_id: int,
        kind: str,
        start_time: datetime,
    ) -> VoiceStateSession:
        session_obj = VoiceStateSession(
            user_id=user_id, guild_id=guild_id, kind=kind, start_time=start_time
        )
        self.session.add(session_obj)
        await self.session.flush()
        return session_obj

    async def earliest_start_time(self, kind: str) -> datetime | None:
        """
        The start_time of the very first tracked session of this kind, across all users.

        This is the "tracking started" cutoff for real vs. estimated data (see
        CONTEXT.md "Engagement") - None means no session of this kind has ever been
        recorded yet (tracking hasn't produced any data for this kind at all).
        """
        result = await self.session.execute(
            select(func.min(VoiceStateSession.start_time)).where(VoiceStateSession.kind == kind)
        )
        earliest = result.scalar_one_or_none()
        return _as_aware_utc(earliest) if earliest is not None else None

    async def get_open_session(self, user_id: int, kind: str) -> VoiceStateSession | None:
        """Finds the user's currently open (unfinished) session of the given kind."""
        result = await self.session.execute(
            select(VoiceStateSession).where(
                VoiceStateSession.user_id == user_id,
                VoiceStateSession.kind == kind,
                VoiceStateSession.end_time.is_(None),
            )
        )
        return result.scalars().first()

    async def close_session(
        self, session_obj: VoiceStateSession, end_time: datetime
    ) -> VoiceStateSession:
        session_obj.end_time = end_time
        session_obj.duration_seconds = _duration_seconds(session_obj.start_time, end_time)
        await self.session.flush()
        return session_obj

    async def close_all_open(self, end_time: datetime) -> None:
        """Closes all 'orphaned' sessions (e.g. after a bot restart)."""
        result = await self.session.execute(
            select(VoiceStateSession).where(VoiceStateSession.end_time.is_(None))
        )
        for session_obj in result.scalars().all():
            session_obj.end_time = end_time
            session_obj.duration_seconds = _duration_seconds(session_obj.start_time, end_time)
        await self.session.flush()

    async def total_time_by_user(
        self,
        kind: str,
        since: datetime | None = None,
        until: datetime | None = None,
        now: datetime | None = None,
    ) -> list[tuple[int, int]]:
        """
        Total time (in seconds) spent with the given state (kind) enabled, grouped by user.

        Same overlap-window (and shared-`now`) semantics as
        `VoiceSessionRepository.total_time_by_user`.
        """
        now = now if now is not None else datetime.now(timezone.utc)
        since_utc = _as_aware_utc(since) if since is not None else None
        until_utc = _as_aware_utc(until) if until is not None else None
        conditions = [VoiceStateSession.kind == kind]
        conditions += _window_conditions(
            since_utc, until_utc, VoiceStateSession.start_time, VoiceStateSession.end_time
        )
        result = await self.session.execute(
            select(
                VoiceStateSession.user_id, VoiceStateSession.start_time, VoiceStateSession.end_time
            ).where(*conditions)
        )
        totals = _sum_overlap_seconds(result.all(), since_utc, until_utc, now)
        return list(totals.items())

    async def engagement_by_user(
        self,
        voice_repo: "VoiceSessionRepository",
        kind: str,
        voice_seconds_by_user: dict[int, int],
        since: datetime | None,
        until: datetime | None,
        now: datetime,
    ) -> tuple[dict[int, int], dict[int, bool]]:
        """
        Per-user (blended_seconds, estimated) for one kind - see CONTEXT.md "Engagement".

        `kind`'s cutoff is the start_time of the very first session of that kind ever
        recorded, across all users (`earliest_start_time`) - there is no real data
        before it, so voice time before the cutoff counts as fully engaged; voice time
        at or after it counts for real. If `kind` has never been tracked at all, the
        cutoff is treated as infinitely far in the future, so the whole window falls
        "before" it. Each kind has its own cutoff: e.g. if the very first member
        tracked after deploy happened to already be muted, the 'unmuted' cutoff lags
        behind the 'undeafened' one. `estimated` is True for a user whenever any of
        *their* counted voice time falls before the cutoff. The blended total is
        clamped to `voice_seconds_by_user` in case tracked state time and voice time
        ever drift apart (they shouldn't, but a state session can never legitimately
        outlast the voice presence it happened within).
        """
        cutoff = await self.earliest_start_time(kind) or datetime.max.replace(tzinfo=timezone.utc)
        until_utc = _as_aware_utc(until) if until is not None else None
        real_seconds_by_user = dict(
            await self.total_time_by_user(kind, since=since, until=until_utc, now=now)
        )
        pre_cutoff_until = min(until_utc, cutoff) if until_utc is not None else min(now, cutoff)
        pre_seconds_by_user = dict(
            await voice_repo.total_time_by_user(since=since, until=pre_cutoff_until, now=now)
        )

        blended: dict[int, int] = {}
        estimated: dict[int, bool] = {}
        for user_id, voice_seconds in voice_seconds_by_user.items():
            pre_seconds = pre_seconds_by_user.get(user_id, 0)
            real_seconds = real_seconds_by_user.get(user_id, 0)
            blended[user_id] = min(pre_seconds + real_seconds, voice_seconds)
            estimated[user_id] = pre_seconds > 0
        return blended, estimated


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
        until: datetime | None = None,
        role_ids: list[int] | None = None,
    ) -> list[tuple[str, int]]:
        """
        Game leaderboard (activity_type == 'playing') by total play time.

        Same overlap-window semantics as `VoiceSessionRepository.total_time_by_user`.
        """
        now = datetime.now(timezone.utc)
        since_utc = _as_aware_utc(since) if since is not None else None
        until_utc = _as_aware_utc(until) if until is not None else None
        conditions = [ActivitySession.activity_type == "playing"]
        conditions += _window_conditions(
            since_utc, until_utc, ActivitySession.start_time, ActivitySession.end_time
        )
        query = select(
            ActivitySession.activity_name, ActivitySession.start_time, ActivitySession.end_time
        ).where(*conditions)
        if role_ids:
            query = query.join(User, User.id == ActivitySession.user_id).where(
                User.role_ids.overlap(role_ids)
            )
        result = await self.session.execute(query)
        totals = _sum_overlap_seconds(result.all(), since_utc, until_utc, now)
        return _aggregate_by_normalized_name(list(totals.items()), limit)

    async def total_game_time_by_user(
        self, user_id: int, since: datetime | None = None, until: datetime | None = None
    ) -> list[tuple[str, int]]:
        """The given user's play time, grouped by game name.

        Same overlap-window semantics as `VoiceSessionRepository.total_time_by_user`.
        """
        now = datetime.now(timezone.utc)
        since_utc = _as_aware_utc(since) if since is not None else None
        until_utc = _as_aware_utc(until) if until is not None else None
        conditions = [
            ActivitySession.user_id == user_id,
            ActivitySession.activity_type == "playing",
        ]
        conditions += _window_conditions(
            since_utc, until_utc, ActivitySession.start_time, ActivitySession.end_time
        )
        result = await self.session.execute(
            select(
                ActivitySession.activity_name, ActivitySession.start_time, ActivitySession.end_time
            ).where(*conditions)
        )
        totals = _sum_overlap_seconds(result.all(), since_utc, until_utc, now)
        return _aggregate_by_normalized_name(list(totals.items()))
