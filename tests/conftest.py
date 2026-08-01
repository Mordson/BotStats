"""Shared pytest fixtures: an isolated in-memory SQLite session per test,
fake discord.py objects, and a FastAPI TestClient wired to the same session."""

from __future__ import annotations

from types import SimpleNamespace
from typing import AsyncIterator, Iterator

import discord
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.deps import get_db_session
from api.main import app
from config import settings
from core.database import Base
from core.services import TrackingService

# Registers the models on Base.metadata before create_all() runs below.
from core import models  # noqa: F401


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def tracking_service(db_session: AsyncSession) -> TrackingService:
    return TrackingService(db_session)


@pytest.fixture
def api_client(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    # visible_role_ids drives a User.role_ids.overlap() query, a Postgres ARRAY
    # operator unsupported on the SQLite test DB - neutralize it here regardless
    # of what's configured in the real .env (role-filtering itself is untested,
    # see "Poza zakresem" in the test plan).
    monkeypatch.setattr(settings, "visible_role_ids", "")

    app.dependency_overrides[get_db_session] = override_get_db_session
    # Not entered as a context manager: that would run the app's lifespan
    # (init_db(), which connects to the real Postgres engine) - the SQLite
    # schema is already created by the db_session fixture above.
    yield TestClient(app)
    del app.dependency_overrides[get_db_session]


def make_role(id: int) -> SimpleNamespace:
    return SimpleNamespace(id=id)


def make_voice_channel(id: int, name: str) -> SimpleNamespace:
    return SimpleNamespace(id=id, name=name)


def make_voice_state(channel: SimpleNamespace | None = None) -> SimpleNamespace:
    return SimpleNamespace(channel=channel)


def make_activity(
    name: str, type: discord.ActivityType = discord.ActivityType.playing
) -> SimpleNamespace:
    return SimpleNamespace(name=name, type=type)


class FakeMember(SimpleNamespace):
    """SimpleNamespace with a real __str__ override.

    services.py calls str(member) to derive the stored username, and
    __str__ is looked up on the type (not the instance), so a plain
    SimpleNamespace kwarg can't provide it - this subclass can.
    """

    def __str__(self) -> str:
        return self.username


def make_member(
    id: int,
    username: str = "someuser",
    display_name: str = "Some User",
    roles: list[SimpleNamespace] | None = None,
    guild_id: int = 1,
    activities: list[SimpleNamespace] | None = None,
) -> FakeMember:
    return FakeMember(
        id=id,
        username=username,
        display_name=display_name,
        roles=roles or [],
        guild=SimpleNamespace(id=guild_id),
        activities=activities or [],
    )
