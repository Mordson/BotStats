"""
API response schemas (DTO / Pydantic).

Decouple the database model (core/models.py) from the API contract,
so changes to the database don't directly affect the dashboard
and vice versa.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

# Discord IDs (snowflakes) exceed JS's safe integer range (2^53),
# so they must reach the frontend as a string, not a JSON number.
Snowflake = Annotated[int, PlainSerializer(str, return_type=str)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Snowflake
    username: str
    display_name: str
    first_seen: datetime


class VoiceTimeOut(BaseModel):
    user_id: Snowflake
    display_name: str
    total_seconds: int


class ChannelTimeOut(BaseModel):
    channel_id: Snowflake
    channel_name: str
    total_seconds: int


class GameTimeOut(BaseModel):
    activity_name: str
    total_seconds: int


# Same shape as a top-games row; kept as its own name for the per-user endpoint.
UserGameTimeOut = GameTimeOut


class GenreTimeOut(BaseModel):
    genre: str
    total_seconds: int
    # The genre's most-played games, descending.
    top_games: list[GameTimeOut]


class EngagementOut(BaseModel):
    user_id: Snowflake
    display_name: str
    voice_seconds: int
    unmuted_seconds: int
    undeafened_seconds: int
    unmuted_percent: float
    undeafened_percent: float
    unmuted_estimated: bool
    undeafened_estimated: bool
