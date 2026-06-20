"""
Cog odpowiedzialny za śledzenie aktywności użytkowników (np. "Playing ...",
"Streaming ...", "Listening to Spotify").

Wymaga włączonego "Presence Intent" w Discord Developer Portal.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from config import settings
from core.database import async_session
from core.services import TrackingService

logger = logging.getLogger("bot.presence_tracker")


class PresenceTrackerCog(commands.Cog):
    """Nasłuchuje zmian statusu/aktywności użytkowników."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_presence_update(
        self,
        before: discord.Member,
        after: discord.Member,
    ) -> None:
        if after.bot:
            return
        if settings.guild_id is not None and after.guild.id != settings.guild_id:
            return

        try:
            async with async_session() as session:
                service = TrackingService(session)
                await service.handle_presence_update(before, after)
        except Exception:  # noqa: BLE001
            logger.exception("Błąd podczas obsługi on_presence_update dla %s", after)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PresenceTrackerCog(bot))
