"""
Shared glue between the tracking cogs and TrackingService.

Every cog listener does the same two things around its own service call:
skip events that shouldn't be tracked, and run the call in a fresh database
session without letting an exception escape into discord.py's event loop.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

import discord

from config import settings
from core.database import async_session
from core.services import TrackingService


def is_tracked(member: discord.Member) -> bool:
    """False for bots and for members of guilds other than the configured one."""
    if member.bot:
        return False
    return settings.guild_id is None or member.guild.id == settings.guild_id


async def run_tracking(
    logger: logging.Logger,
    event: str,
    member: discord.Member,
    handle: Callable[[TrackingService], Awaitable[None]],
) -> None:
    """Runs `handle` with a TrackingService on a new session, logging (not raising) any error."""
    try:
        async with async_session() as session:
            await handle(TrackingService(session))
    except Exception:  # noqa: BLE001
        logger.exception("Błąd podczas obsługi %s dla %s", event, member)
