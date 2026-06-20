"""
Cog odpowiedzialny za śledzenie czasu spędzonego na kanałach głosowych.

Sam nie zawiera logiki biznesowej - delegowanie do TrackingService
(core/services.py) zgodnie z zasadą separacji warstw.
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
    """Nasłuchuje zmian stanu głosowego (wejście/wyjście/zmiana kanału)."""

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
