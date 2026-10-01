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

from bot.tracking import is_tracked, run_tracking

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
        if not is_tracked(after) or before.roles == after.roles:
            return
        await run_tracking(
            logger, "on_member_update", after, lambda service: service.sync_member(after)
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MemberTrackerCog(bot))
