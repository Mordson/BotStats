"""
Entry point for the Discord bot.

Responsible for:
- configuring the intents required for tracking,
- initializing the database,
- loading the cogs (feature modules),
- cleaning up "orphaned" sessions after a restart.
"""

from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from config import settings
from core.database import async_session, init_db

# IMPORTANT: models must be imported BEFORE init_db(), so their tables
# get registered on Base.metadata.
from core import models  # noqa: F401
from core.services import TrackingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bot")


def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    # Required to read the guild's member list/activities.
    # NOTE: these are "privileged intents" - they must be enabled
    # in the Discord Developer Portal -> Bot -> Privileged Gateway Intents.
    intents.members = True
    intents.presences = True
    intents.voice_states = True
    return intents


bot = commands.Bot(command_prefix="!", intents=build_intents())

EXTENSIONS = [
    "bot.cogs.voice_tracker",
    "bot.cogs.presence_tracker",
    "bot.cogs.member_tracker",
]


@bot.event
async def on_ready() -> None:
    logger.info("Zalogowano jako %s (ID: %s)", bot.user, bot.user.id if bot.user else "?")

    # After a (re)start, close any sessions left "open" in the database,
    # so they don't count time since the last restart as a single session.
    async with async_session() as session:
        service = TrackingService(session)
        await service.cleanup_open_sessions()

    logger.info("Wyczyszczono otwarte sesje pozostałe po poprzednim uruchomieniu.")

    # Open sessions for activities and voice presence already in progress at
    # bot startup. on_presence_update / on_voice_state_update only fire on
    # changes, so state from before the bot came online is initialized here.
    async with async_session() as session:
        service = TrackingService(session)
        for guild in bot.guilds:
            # Same guild filter as the cogs - otherwise sessions would be opened
            # in guilds whose live events are ignored, and never closed.
            if settings.guild_id is not None and guild.id != settings.guild_id:
                continue
            for member in guild.members:
                if member.bot:
                    continue
                await service.sync_member_activities(member)
                await service.sync_member_voice(member)
        await session.commit()

    logger.info("Zsynchronizowano aktywności i stan głosowy w momencie startu bota.")


async def main() -> None:
    await init_db()

    async with bot:
        for extension in EXTENSIONS:
            await bot.load_extension(extension)
            logger.info("Wczytano rozszerzenie: %s", extension)

        await bot.start(settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
