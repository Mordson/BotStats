"""
Schematy odpowiedzi API (DTO / Pydantic).

Oddzielają model bazy danych (core/models.py) od kontraktu API,
żeby zmiany w bazie nie wpływały bezpośrednio na dashboard
i odwrotnie.
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
        # ID Discorda (snowflake) przekraczają bezpieczny zakres liczb w JS (2^53),
        # więc muszą trafiać do frontendu jako string, nie liczba JSON.
        return str(value)


class VoiceTimeOut(BaseModel):
    user_id: int
    display_name: str
    total_seconds: int

    @field_serializer("user_id")
    def serialize_user_id(self, value: int) -> str:
        return str(value)


class GameTimeOut(BaseModel):
    activity_name: str
    total_seconds: int


class UserGameTimeOut(BaseModel):
    activity_name: str
    total_seconds: int
