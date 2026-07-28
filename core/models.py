"""
ORM models (SQLAlchemy 2.0, Mapped/mapped_column style).

Tables:
- users            - Discord users seen on the guild
- voice_sessions   - sessions of presence in voice channels (for counting "time on server")
- activity_sessions - activity sessions (e.g. "Playing Valorant", "Listening to Spotify")
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class User(Base):
    __tablename__ = "users"

    # The Discord user ID (Snowflake) doubles as our PK
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(100))
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now()
    )
    # The user's current role IDs on the guild (refreshed on every member sync),
    # used to filter visibility in the dashboard's game sections.
    role_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger).with_variant(JSON(), "sqlite"), default=list, server_default="{}"
    )

    voice_sessions: Mapped[list["VoiceSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    activity_sessions: Mapped[list["ActivitySession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} display_name={self.display_name!r}>"


class VoiceSession(Base):
    """A single session of presence in a voice channel."""

    __tablename__ = "voice_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    channel_name: Mapped[str] = mapped_column(String(100))

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="voice_sessions")

    def __repr__(self) -> str:
        return (
            f"<VoiceSession user_id={self.user_id} channel={self.channel_name!r} "
            f"start={self.start_time} end={self.end_time}>"
        )


class ActivitySession(Base):
    """
    A single activity session (e.g. a game, streaming status).

    activity_type corresponds to discord.ActivityType: 'playing', 'streaming',
    'listening', 'watching', 'competing'.
    """

    __tablename__ = "activity_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)

    activity_name: Mapped[str] = mapped_column(String(150), index=True)
    activity_type: Mapped[str] = mapped_column(String(30))

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped["User"] = relationship(back_populates="activity_sessions")

    def __repr__(self) -> str:
        return (
            f"<ActivitySession user_id={self.user_id} activity={self.activity_name!r} "
            f"type={self.activity_type} start={self.start_time} end={self.end_time}>"
        )
