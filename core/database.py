"""
Warstwa dostępu do bazy danych.

Definiuje:
- `Base` - klasę bazową dla modeli ORM (core/models.py),
- `engine` / `async_session` - silnik i fabrykę sesji SQLAlchemy (async, asyncpg),
- `init_db()` - tworzenie tabel na podstawie modeli (do dev/testów;
  w produkcji zaleca się migracje, np. Alembic).
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    """Klasa bazowa dla wszystkich modeli ORM."""


engine = create_async_engine(settings.database_url, echo=False, future=True)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """
    Tworzy tabele w bazie na podstawie zarejestrowanych modeli.

    UWAGA: modele muszą być zaimportowane (zarejestrowane na Base.metadata)
    PRZED wywołaniem tej funkcji - patrz `from core import models` w main.py.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
