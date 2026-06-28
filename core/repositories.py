"""
Warstwa repozytoriów (Repository pattern).

Każde repozytorium odpowiada za zapytania dotyczące jednej tabeli/modelu.
Dzięki temu warstwa serwisowa (core/services.py) i API (api/) nie piszą
zapytań SQL/ORM samodzielnie - operują na metodach repozytoriów.

Jeśli w przyszłości baza danych się zmieni (np. inna struktura tabel,
inny silnik), zmiany powinny dotyczyć tylko tego pliku.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import ActivitySession, User, VoiceSession


def _as_aware_utc(value: datetime) -> datetime:
    """
    Normalizuje datetime do timezone-aware UTC.

    Niektóre bazy/dialekty (np. SQLite) mogą zwracać naiwne datetime
    nawet jeśli kolumna jest zadeklarowana jako DateTime(timezone=True).
    Ta funkcja zapewnia, że odejmowanie dwóch znaczników czasu zawsze
    zadziała, niezależnie od backendu.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _duration_seconds(start: datetime, end: datetime) -> int:
    return int((_as_aware_utc(end) - _as_aware_utc(start)).total_seconds())


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self, user_id: int, username: str, display_name: str) -> User:
        """Zwraca istniejącego użytkownika albo tworzy nowy wpis i odświeża dane profilu."""
        user = await self.session.get(User, user_id)
        if user is None:
            user = User(id=user_id, username=username, display_name=display_name)
            self.session.add(user)
            await self.session.flush()
        else:
            user.username = username
            user.display_name = display_name
        return user

    async def get_all(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.display_name))
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
        """Znajduje aktualnie otwartą (niezakończoną) sesję głosową użytkownika."""
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
        """Zamyka wszystkie 'osierocone' sesje (np. po restarcie bota)."""
        result = await self.session.execute(
            select(VoiceSession).where(VoiceSession.end_time.is_(None))
        )
        for session_obj in result.scalars().all():
            session_obj.end_time = end_time
            session_obj.duration_seconds = _duration_seconds(session_obj.start_time, end_time)
        await self.session.flush()


    async def total_time_by_user(self) -> list[tuple[int, int]]:
        """Suma czasu (w sekundach) na kanałach głosowych, pogrupowana po użytkowniku."""
        result = await self.session.execute(
            select(VoiceSession.user_id, func.sum(VoiceSession.duration_seconds))
            .where(VoiceSession.duration_seconds.is_not(None))
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
        Znajduje otwartą sesję dla danej aktywności użytkownika.

        Użytkownik może mieć kilka otwartych sesji jednocześnie (np. gra +
        słucha Spotify), więc dopasowujemy po nazwie aktywności.
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

    async def top_games(self, limit: int = 10) -> list[tuple[str, int]]:
        """Ranking gier (activity_type == 'playing') po sumarycznym czasie gry."""
        total = func.sum(ActivitySession.duration_seconds)
        group_key = func.lower(func.trim(ActivitySession.activity_name))
        result = await self.session.execute(
            select(func.min(ActivitySession.activity_name), total)
            .where(
                ActivitySession.activity_type == "playing",
                ActivitySession.duration_seconds.is_not(None),
            )
            .group_by(group_key)
            .order_by(total.desc())
            .limit(limit)
        )
        return [(name, seconds or 0) for name, seconds in result.all()]

    async def total_game_time_by_user(self, user_id: int) -> list[tuple[str, int]]:
        """Czas gry danego użytkownika, pogrupowany po nazwie gry."""
        total = func.sum(ActivitySession.duration_seconds)
        group_key = func.lower(func.trim(ActivitySession.activity_name))
        result = await self.session.execute(
            select(func.min(ActivitySession.activity_name), total)
            .where(
                ActivitySession.user_id == user_id,
                ActivitySession.activity_type == "playing",
                ActivitySession.duration_seconds.is_not(None),
            )
            .group_by(group_key)
            .order_by(total.desc())
        )
        return [(name, seconds or 0) for name, seconds in result.all()]
