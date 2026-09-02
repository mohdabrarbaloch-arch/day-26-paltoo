"""Paltoo - application configuration.

All secrets and environment-specific values live in environment variables.
Never hardcode keys. See .env.example for the full list.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Paltoo"
    app_env: str = "development"  # development | production
    debug: bool = False

    # Security
    secret_key: str = "dev-only-change-me-in-production"  # override via env in production
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24  # 24h

    # Database
    database_url: str = "sqlite:///./paltoo.db"

    # CORS
    cors_origins: str = "*"  # comma-separated list, e.g. "https://app.example.com"

    # Rate limits
    rate_register: str = "5/minute"
    rate_login: str = "10/minute"
    rate_default: str = "60/minute"

    # Business rules
    slot_minutes: int = 30
    clinic_open_hour: int = 10  # 10:00 AM
    clinic_close_hour: int = 20  # 8:00 PM (last slot start 19:30)
    booking_days_ahead: int = 14

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
