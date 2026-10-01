"""
Cog responsible for tracking user activities (e.g. "Playing ...",
"Streaming ...", "Listening to Spotify").

Requires the "Presence Intent" to be enabled in the Discord Developer Portal.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.tracking import is_tracked, run_tracking

logger = logging.getLogger("bot.presence_tracker")


class PresenceTrackerCog(commands.Cog):
    """Listens for user status/activity changes."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_presence_update(
        self,
        before: discord.Member,
        after: discord.Member,
    ) -> None:
        if not is_tracked(after):
            return
        await run_tracking(
            logger,
            "on_presence_update",
            after,
            lambda service: service.handle_presence_update(before, after),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PresenceTrackerCog(bot))
