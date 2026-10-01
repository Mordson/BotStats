"""
Cog responsible for tracking time spent in voice channels.

Contains no business logic itself - delegates to TrackingService
(core/services.py) following the layer-separation principle.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.tracking import is_tracked, run_tracking

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
        if not is_tracked(member):
            return
        await run_tracking(
            logger,
            "on_voice_state_update",
            member,
            lambda service: service.handle_voice_state_update(member, before, after),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceTrackerCog(bot))
