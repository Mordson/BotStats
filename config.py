"""
Central application configuration.

Shared by the bot (bot/) and the API (api/), so both parts use the same
settings (e.g. the database connection string).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Discord bot token (from the Discord Developer Portal)
    discord_token: str

    # Discord guild ID to track (right-click the server -> Copy ID)
    # If not set, the bot tracks all guilds (not recommended)
    guild_id: int | None = None

    # PostgreSQL connection string (async driver: asyncpg)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/discord_activity"

    # Optional: restrict the API to a specific dashboard domain
    cors_origins: str = "*"

    # Discord role IDs (CSV) allowed to appear in the dashboard's game
    # sections (game leaderboard, per-user game stats).
    # Empty = no filtering (everyone is shown).
    visible_role_ids: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def visible_role_ids_list(self) -> list[int]:
        return [int(role_id) for role_id in self.visible_role_ids.split(",") if role_id.strip()]


settings = Settings()
