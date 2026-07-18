"""
Centralna konfiguracja aplikacji.

Współdzielona przez bota (bot/) i API (api/), dzięki czemu obie części
korzystają z tych samych ustawień (np. connection string do bazy danych).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Token bota Discord (z Discord Developer Portal)
    discord_token: str

    # ID serwera Discord do śledzenia (prawy klik na serwer -> Kopiuj ID)
    # Jeśli nie ustawione, bot śledzi wszystkie serwery (niezalecane)
    guild_id: int | None = None

    # Connection string do PostgreSQL (driver async: asyncpg)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/discord_activity"

    # Opcjonalnie: ogranicz API do konkretnej domeny dashboardu
    cors_origins: str = "*"

    # ID ról Discord (CSV), które uprawniają do pokazania się w sekcjach z grami
    # dashboardu (ranking gier, statystyki gier użytkownika).
    # Puste = brak filtrowania (pokazywani są wszyscy).
    visible_role_ids: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def visible_role_ids_list(self) -> list[int]:
        return [int(role_id) for role_id in self.visible_role_ids.split(",") if role_id.strip()]


settings = Settings()
