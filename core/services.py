"""
Warstwa serwisowa (Service layer).

`TrackingService` zawiera logikę biznesową łączącą eventy z discord.py
z repozytoriami. To jedyne miejsce, które "wie", jak interpretować
zmiany VoiceState/Presence i przekładać je na sesje w bazie danych.

Cogi (bot/cogs/) powinny być "głupie" - tylko nasłuchują eventów
i wywołują metody tego serwisu.
"""

from __future__ import annotations

from datetime import datetime, timezone

import discord
from sqlalchemy.ext.asyncio import AsyncSession

from core.repositories import ActivitySessionRepository, UserRepository, VoiceSessionRepository, _normalize_activity_name


class TrackingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.voice = VoiceSessionRepository(session)
        self.activities = ActivitySessionRepository(session)

    async def ensure_user(self, member: discord.Member) -> None:
        """Upewnia się, że użytkownik istnieje w bazie (i aktualizuje jego nazwę)."""
        await self.users.get_or_create(member.id, str(member), member.display_name)

    async def handle_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """
        Obsługuje on_voice_state_update:
        - wejście na kanał -> otwiera nową sesję,
        - wyjście z kanału / zmiana kanału -> zamyka poprzednią sesję,
        - zmiana kanału -> zamyka starą i otwiera nową (jedna sesja per kanał).
        """
        now = datetime.now(timezone.utc)
        await self.ensure_user(member)

        left_channel = before.channel is not None and (
            after.channel is None or after.channel.id != before.channel.id
        )
        joined_channel = after.channel is not None and (
            before.channel is None or before.channel.id != after.channel.id
        )

        if left_channel:
            open_session = await self.voice.get_open_session(member.id)
            if open_session is not None:
                await self.voice.close_session(open_session, now)

        if joined_channel:
            assert after.channel is not None
            await self.voice.start_session(
                user_id=member.id,
                guild_id=member.guild.id,
                channel_id=after.channel.id,
                channel_name=after.channel.name,
                start_time=now,
            )

        await self.session.commit()

    async def handle_presence_update(
        self,
        before: discord.Member,
        after: discord.Member,
    ) -> None:
        """
        Obsługuje on_presence_update:
        porównuje aktywności (gry, streaming, Spotify itd.) przed i po,
        zamykając/otwierając odpowiednie sesje w activity_sessions.
        """
        now = datetime.now(timezone.utc)
        await self.ensure_user(after)

        before_activities = self._relevant_activities(before)
        after_activities = self._relevant_activities(after)

        # Aktywności, które się zakończyły
        for key, activity in before_activities.items():
            if key not in after_activities:
                open_session = await self.activities.get_open_session(
                    after.id, _normalize_activity_name(activity.name)
                )
                if open_session is not None:
                    await self.activities.close_session(open_session, now)

        # Aktywności, które się zaczęły
        for key, activity in after_activities.items():
            if key not in before_activities:
                await self.activities.start_session(
                    user_id=after.id,
                    guild_id=after.guild.id,
                    activity_name=_normalize_activity_name(activity.name),
                    activity_type=activity.type.name,
                    start_time=now,
                )

        await self.session.commit()

    async def sync_member_activities(self, member: discord.Member) -> None:
        """
        Otwiera sesje dla aktywności aktualnie trwających w momencie wywołania.

        Wywoływane przy starcie bota, żeby nie pominąć aktywności rozpoczętych
        przed uruchomieniem bota (bot nie dostaje on_presence_update dla już
        trwających aktywności - tylko dla zmian).
        """
        now = datetime.now(timezone.utc)
        await self.ensure_user(member)

        for activity in self._relevant_activities(member).values():
            normalized = _normalize_activity_name(activity.name)
            open_session = await self.activities.get_open_session(member.id, normalized)
            if open_session is None:
                await self.activities.start_session(
                    user_id=member.id,
                    guild_id=member.guild.id,
                    activity_name=normalized,
                    activity_type=activity.type.name,
                    start_time=now,
                )

    async def cleanup_open_sessions(self) -> None:
        """
        Zamyka wszystkie sesje pozostawione "otwarte" (np. po crashu/restarcie bota),
        żeby nie zaburzały statystyk nieskończonym czasem trwania.
        Wywoływane raz, w on_ready.
        """
        now = datetime.now(timezone.utc)
        await self.voice.close_all_open(now)
        await self.activities.close_all_open(now)
        await self.session.commit()

    @staticmethod
    def _relevant_activities(member: discord.Member) -> dict[str, discord.BaseActivity]:
        """
        Filtruje aktywności użytkownika do tych, które chcemy śledzić.

        Pomija ActivityType.custom (status własny, np. "🎧 w skupieniu"),
        bo zmienia się bardzo często i nie reprezentuje "gry"/aktywności.
        """
        result: dict[str, discord.BaseActivity] = {}
        for activity in member.activities:
            if activity.type == discord.ActivityType.custom:
                continue
            name = getattr(activity, "name", None)
            if not name:
                continue
            key = f"{activity.type.name}:{_normalize_activity_name(name)}"
            result[key] = activity
        return result
