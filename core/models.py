"""
Modele ORM (SQLAlchemy 2.0, styl Mapped/mapped_column).

Tabele:
- users            - użytkownicy Discord widziani na serwerze
- voice_sessions   - sesje pobytu na kanałach głosowych (do liczenia "czasu na serwerze")
- activity_sessions - sesje aktywności (np. "Playing Valorant", "Listening to Spotify")
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class User(Base):
    __tablename__ = "users"

    # ID użytkownika Discord (Snowflake) jest jednocześnie naszym PK
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(100))
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now()
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
    """Pojedyncza sesja przebywania na kanale głosowym."""

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
    Pojedyncza sesja aktywności (np. gra, status streamingu).

    activity_type odpowiada discord.ActivityType: 'playing', 'streaming',
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
