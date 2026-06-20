"""Endpointy API ze statystykami zbiorczymi (dla dashboardu)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db_session
from api.schemas import GameTimeOut, VoiceTimeOut
from core.repositories import ActivitySessionRepository, UserRepository, VoiceSessionRepository

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/voice-time", response_model=list[VoiceTimeOut])
async def voice_time_leaderboard(
    session: AsyncSession = Depends(get_db_session),) -> list[VoiceTimeOut]:
    """Ranking użytkowników po sumarycznym czasie spędzonym na kanałach głosowych."""
    voice_repo = VoiceSessionRepository(session)
    user_repo = UserRepository(session)

    rows = await voice_repo.total_time_by_user()
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


@router.get("/top-games", response_model=list[GameTimeOut])
async def top_games(
    limit: int = 10,
    session: AsyncSession = Depends(get_db_session),
) -> list[GameTimeOut]:
    """Ranking gier po sumarycznym czasie gry wszystkich użytkowników."""
    repo = ActivitySessionRepository(session)
    rows = await repo.top_games(limit=limit)
    return [GameTimeOut(activity_name=name, total_seconds=seconds) for name, seconds in rows]
