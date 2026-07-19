"""
Database access layer.

Defines:
- `Base` - the base class for the ORM models (core/models.py),
- `engine` / `async_session` - the SQLAlchemy engine and session factory (async, asyncpg),
- `init_db()` - creates tables from the models (for dev/tests;
  migrations, e.g. Alembic, are recommended in production).
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""


engine = create_async_engine(settings.database_url, echo=False, future=True)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """
    Creates the database tables from the registered models.

    NOTE: models must be imported (registered on Base.metadata)
    BEFORE calling this function - see `from core import models` in main.py.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
