from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Collectarr Sync"
    environment: str = "development"
    sync_database_path: str = "./collectarr-sync.db"
    sync_api_key: str = Field(default="collectarr-sync-dev-key")
    sync_change_retention_days: int = Field(default=90, ge=1)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def require_sync_key_outside_dev(self) -> "Settings":
        if self.environment not in {"development", "test"}:
            if not self.sync_api_key or self.sync_api_key == "collectarr-sync-dev-key":
                raise ValueError("SYNC_API_KEY must be set outside development/test")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
