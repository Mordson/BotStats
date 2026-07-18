"""Endpointy API związane z użytkownikami."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db_session
from api.schemas import UserGameTimeOut, UserOut
from core.repositories import ActivitySessionRepository, UserRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
async def list_users(session: AsyncSession = Depends(get_db_session)) -> list[UserOut]:
    """Lista wszystkich znanych użytkowników serwera."""
    repo = UserRepository(session)
    users = await repo.get_all()
    return [UserOut.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, session: AsyncSession = Depends(get_db_session)) -> UserOut:
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    return UserOut.model_validate(user)


@router.get("/{user_id}/games", response_model=list[UserGameTimeOut])
async def user_game_time(
    user_id: int, session: AsyncSession = Depends(get_db_session)
) -> list[UserGameTimeOut]:
    """Czas gry danego użytkownika w poszczególnych grach (sekundy)."""
    repo = ActivitySessionRepository(session)
    rows = await repo.total_game_time_by_user(user_id)
    return [UserGameTimeOut(activity_name=name, total_seconds=seconds) for name, seconds in rows]
