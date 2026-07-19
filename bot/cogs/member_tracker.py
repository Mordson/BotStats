"""
Cog responsible for tracking changes to users' roles.

The voice/presence trackers refresh roles "incidentally" (via ensure_user), but
a role change alone (e.g. granting/removing a rank) without a status/activity
change wouldn't trigger either of those events - hence a separate listener on
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
    """Listens for changes to a guild member's data (including roles)."""

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
