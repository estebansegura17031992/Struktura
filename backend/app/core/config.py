"""Configuración centralizada con pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    APP_NAME: str = "Kanban MVP"
    APP_VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""

    # JWT
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Email
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "noreply@example.com"
    EMAIL_DEV_MODE: bool = True

    # Features
    ENABLE_DOCS: bool = True
    RATE_LIMIT_ENABLED: bool = True

    # Tests — cuando es True el rate limiting se desactiva en tests
    TESTING: bool = False

    @field_validator("JWT_SECRET")
    @classmethod
    def jwt_secret_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET debe tener al menos 32 caracteres")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        """staging y production usan cookies Secure y sin stack traces en responses."""
        return self.ENVIRONMENT in ("production", "staging")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
