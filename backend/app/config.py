from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, read from environment variables (or a .env file)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = ""
    telegram_channel_id: str = ""

    database_url: str = "sqlite+aiosqlite:///./data/organizer.db"
    media_dir: Path = Path("./data/media")
    timezone: str = "Asia/Tashkent"
    scheduler_poll_seconds: int = 30
    scheduler_enabled: bool = True

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_channel_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
