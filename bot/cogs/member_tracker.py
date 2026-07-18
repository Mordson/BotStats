"""
Cog odpowiedzialny za śledzenie zmian ról użytkowników.

Voice/presence tracker odświeżają role "przy okazji" (przez ensure_user), ale
zmiana samych ról (np. nadanie/odebranie rangi) bez zmiany statusu/aktywności
nie wywołałaby żadnego z tamtych eventów - stąd osobny listener na
on_member_update.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from config import settings
from core.database import async_session
from core.services import TrackingService

logger = logging.getLogger("bot.member_tracker")


class MemberTrackerCog(commands.Cog):
    """Nasłuchuje zmian danych członka serwera (m.in. ról)."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(
        self,
        before: discord.Member,
        after: discord.Member,
    ) -> None:
        if after.bot:
            return
        if settings.guild_id is not None and after.guild.id != settings.guild_id:
            return
        if before.roles == after.roles:
            return

        try:
            async with async_session() as session:
                service = TrackingService(session)
                await service.sync_member(after)
        except Exception:  # noqa: BLE001
            logger.exception("Błąd podczas obsługi on_member_update dla %s", after)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MemberTrackerCog(bot))
