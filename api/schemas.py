"""
API response schemas (DTO / Pydantic).

Decouple the database model (core/models.py) from the API contract,
so changes to the database don't directly affect the dashboard
and vice versa.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    first_seen: datetime

    @field_serializer("id")
    def serialize_id(self, value: int) -> str:
        # Discord IDs (snowflakes) exceed JS's safe integer range (2^53),
        # so they must reach the frontend as a string, not a JSON number.
        return str(value)


class VoiceTimeOut(BaseModel):
    user_id: int
    display_name: str
    total_seconds: int

    @field_serializer("user_id")
    def serialize_user_id(self, value: int) -> str:
        return str(value)


class ChannelTimeOut(BaseModel):
    channel_id: int
    channel_name: str
    total_seconds: int

    @field_serializer("channel_id")
    def serialize_channel_id(self, value: int) -> str:
        return str(value)


class GameTimeOut(BaseModel):
    activity_name: str
    total_seconds: int


class UserGameTimeOut(BaseModel):
    activity_name: str
    total_seconds: int
