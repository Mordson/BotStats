"""
Punkt wejścia bota Discord.

Odpowiada za:
- konfigurację intencji (intents) wymaganych do trackingu,
- inicjalizację bazy danych,
- wczytanie cogów (modułów funkcjonalnych),
- czyszczenie "osieroconych" sesji po restarcie.
"""

from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from config import settings
from core.database import async_session, init_db

# WAŻNE: import modeli musi nastąpić PRZED init_db(), żeby ich tabele
# zostały zarejestrowane na Base.metadata.
from core import models  # noqa: F401
from core.services import TrackingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bot")


def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    # Wymagane do odczytu listy/aktywności członków serwera.
    # UWAGA: to są "privileged intents" - muszą być włączone
    # w Discord Developer Portal -> Bot -> Privileged Gateway Intents.
    intents.members = True
    intents.presences = True
    intents.voice_states = True
    return intents


bot = commands.Bot(command_prefix="!", intents=build_intents())

EXTENSIONS = [
    "bot.cogs.voice_tracker",
    "bot.cogs.presence_tracker",
]


@bot.event
async def on_ready() -> None:
    logger.info("Zalogowano jako %s (ID: %s)", bot.user, bot.user.id if bot.user else "?")

    # Po (re)starcie zamykamy sesje, które zostały "otwarte" w bazie,
    # żeby nie liczyły czasu od ostatniego restartu jako jednej sesji.
    async with async_session() as session:
        service = TrackingService(session)
        await service.cleanup_open_sessions()

    logger.info("Wyczyszczono otwarte sesje pozostałe po poprzednim uruchomieniu.")

    # Otwieramy sesje dla aktywności już trwających w momencie startu bota.
    # on_presence_update nie jest emitowane dla aktywności, które zaczęły się
    # przed uruchomieniem bota, więc musimy je zainicjalizować ręcznie.
    async with async_session() as session:
        service = TrackingService(session)
        for guild in bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                await service.sync_member_activities(member)
        await session.commit()

    logger.info("Zsynchronizowano aktywności trwające w momencie startu bota.")


async def main() -> None:
    await init_db()

    async with bot:
        for extension in EXTENSIONS:
            await bot.load_extension(extension)
            logger.info("Wczytano rozszerzenie: %s", extension)

        await bot.start(settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
