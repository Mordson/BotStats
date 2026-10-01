import logging
from types import SimpleNamespace

import pytest

from bot import tracking
from config import settings


def _member(bot: bool = False, guild_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(bot=bot, guild=SimpleNamespace(id=guild_id))


def test_is_tracked_skips_bots(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "guild_id", None)
    assert tracking.is_tracked(_member(bot=True)) is False


def test_is_tracked_accepts_any_guild_when_unconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "guild_id", None)
    assert tracking.is_tracked(_member(guild_id=42)) is True


def test_is_tracked_filters_other_guilds(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "guild_id", 1)
    assert tracking.is_tracked(_member(guild_id=1)) is True
    assert tracking.is_tracked(_member(guild_id=2)) is False


async def test_run_tracking_passes_a_service_to_the_handler(monkeypatch, db_session):
    monkeypatch.setattr(tracking, "async_session", lambda: db_session)
    received = []

    async def handle(service):
        received.append(service)

    await tracking.run_tracking(logging.getLogger("test"), "on_test", _member(), handle)

    assert len(received) == 1
    assert received[0].session is db_session


async def test_run_tracking_logs_instead_of_raising(monkeypatch, db_session, caplog):
    monkeypatch.setattr(tracking, "async_session", lambda: db_session)

    async def handle(service):
        raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR):
        await tracking.run_tracking(logging.getLogger("test"), "on_test", _member(), handle)

    assert "on_test" in caplog.text
