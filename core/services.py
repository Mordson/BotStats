"""
Service layer.

`TrackingService` contains the business logic connecting discord.py events
to the repositories. It is the only place that "knows" how to interpret
VoiceState/Presence changes and translate them into database sessions.

Cogs (bot/cogs/) should be "dumb" - they only listen for events
and call methods on this service.
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
        """Ensures the user exists in the database (and updates their name and roles)."""
        role_ids = [role.id for role in member.roles]
        await self.users.get_or_create(member.id, str(member), member.display_name, role_ids)

    async def sync_member(self, member: discord.Member) -> None:
        """Refreshes the user's profile and roles (e.g. after a role change) and saves the changes."""
        await self.ensure_user(member)
        await self.session.commit()

    async def handle_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """
        Handles on_voice_state_update:
        - joining a channel -> opens a new session,
        - leaving a channel / switching channels -> closes the previous session,
        - switching channels -> closes the old one and opens a new one (one session per channel).
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
        Handles on_presence_update:
        compares activities (games, streaming, Spotify, etc.) before and after,
        closing/opening the corresponding sessions in activity_sessions.
        """
        now = datetime.now(timezone.utc)
        await self.ensure_user(after)

        before_activities = self._relevant_activities(before)
        after_activities = self._relevant_activities(after)

        # Activities that ended
        for key, activity in before_activities.items():
            if key not in after_activities:
                open_session = await self.activities.get_open_session(
                    after.id, _normalize_activity_name(activity.name)
                )
                if open_session is not None:
                    await self.activities.close_session(open_session, now)

        # Activities that started
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
        Opens sessions for activities currently in progress at the time of the call.

        Called on bot startup, so activities that started before the bot came
        online aren't missed (the bot doesn't get on_presence_update for
        already-ongoing activities - only for changes).
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
        Closes all sessions left "open" (e.g. after a bot crash/restart),
        so they don't skew statistics with an infinite duration.
        Called once, in on_ready.
        """
        now = datetime.now(timezone.utc)
        await self.voice.close_all_open(now)
        await self.activities.close_all_open(now)
        await self.session.commit()

    @staticmethod
    def _relevant_activities(member: discord.Member) -> dict[str, discord.BaseActivity]:
        """
        Filters the user's activities down to the ones we want to track.

        Skips ActivityType.custom (a custom status, e.g. "🎧 focusing"),
        since it changes very often and doesn't represent a "game"/activity.
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
