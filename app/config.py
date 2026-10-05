from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    telegram_bot_token: str
    telegram_channel_id: str
    telegram_channel_link: str = ""
    admin_telegram_ids: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./german_bot.db"

    # LLM (OpenAI only)
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None

    # Scheduling
    timezone: str = "Asia/Tashkent"
    post_times: str = "08:00,12:00,16:00,20:00,22:00"

    # Content strategy
    promotional_post_ratio: float = 0.10
    duplicate_similarity_threshold: float = 0.80
    max_generation_attempts: int = 3
    default_cefr_level: str = "Mixed"

    # News
    news_enabled: bool = False
    news_api_key: str = ""

    # Marketing
    german_classes_contact: str = "@your_contact"

    # Health check
    health_check_host: str = "0.0.0.0"
    health_check_port: int = 8080

    # Logging
    log_level: str = "INFO"

    @property
    def channel_link(self) -> str:
        """Public URL for the channel footer. Falls back to the channel ID
        when it's already an @username; for private channels or numeric IDs,
        set TELEGRAM_CHANNEL_LINK explicitly (e.g. an invite link)."""
        if self.telegram_channel_link:
            return self.telegram_channel_link
        if self.telegram_channel_id.startswith("@"):
            return f"https://t.me/{self.telegram_channel_id.lstrip('@')}"
        return self.telegram_channel_id

    @property
    def admin_ids(self) -> list[int]:
        return [int(x.strip()) for x in self.admin_telegram_ids.split(",") if x.strip()]

    @property
    def post_times_list(self) -> list[str]:
        return [t.strip() for t in self.post_times.split(",") if t.strip()]

    @field_validator("promotional_post_ratio", "duplicate_similarity_threshold")
    @classmethod
    def _validate_ratio(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("ratio must be between 0 and 1")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
