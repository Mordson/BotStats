"""
Cog responsible for tracking time spent in voice channels.

Contains no business logic itself - delegates to TrackingService
(core/services.py) following the layer-separation principle.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from config import settings
from core.database import async_session
from core.services import TrackingService

logger = logging.getLogger("bot.voice_tracker")


class VoiceTrackerCog(commands.Cog):
    """Listens for voice state changes (join/leave/channel switch)."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return
        if settings.guild_id is not None and member.guild.id != settings.guild_id:
            return

        try:
            async with async_session() as session:
                service = TrackingService(session)
                await service.handle_voice_state_update(member, before, after)
        except Exception:  # noqa: BLE001
            logger.exception("Błąd podczas obsługi on_voice_state_update dla %s", member)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceTrackerCog(bot))
