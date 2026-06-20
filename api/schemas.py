"""
Schematy odpowiedzi API (DTO / Pydantic).

Oddzielają model bazy danych (core/models.py) od kontraktu API,
żeby zmiany w bazie nie wpływały bezpośrednio na dashboard
i odwrotnie.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    first_seen: datetime


class VoiceTimeOut(BaseModel):
    user_id: int
    display_name: str
    total_seconds: int


class GameTimeOut(BaseModel):
    activity_name: str
    total_seconds: int


class UserGameTimeOut(BaseModel):
    activity_name: str
    total_seconds: int
