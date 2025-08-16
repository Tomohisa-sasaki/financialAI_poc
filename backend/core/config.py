
from __future__ import annotations
from pydantic import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application configuration loaded from environment variables (.env).

    NOTE: This preserves existing field names for backward compatibility.
    """

    # --- Security / Auth ---
    API_USER: str = "admin"
    API_PASSWORD: str = "password123"

    # --- Runtime / Logging ---
    ENV: str = "development"  # development | staging | production
    LOG_LEVEL: str = "INFO"    # INFO, DEBUG, WARNING, ERROR
    JSON_LOGS: bool = False
    LOG_FILE_PATH: str | None = None

    # --- OpenAI (optional) ---
    OPENAI_API_KEY: str | None = None

    # --- Email ---
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASS: str | None = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM: str | None = None
    SENDGRID_API_KEY: str | None = None

    # --- Data sources (J-Quants / EDINET) ---
    JQ_EMAIL: str | None = None
    JQ_PASSWORD: str | None = None
    JQ_REFRESH_TOKEN: str | None = None  # if you cache refresh tokens

    # --- Database (optional) ---
    DATABASE_URL: str | None = None

    # --- CORS ---
    CORS_ALLOW_ORIGINS: str = "*"  # comma-separated list or "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    # Helper: parse comma-separated origins → list, with fallback
    @property
    def cors_origins(self) -> List[str]:
        raw = (self.CORS_ALLOW_ORIGINS or "*").strip()
        if raw == "*":
            return ["*"]
        return [s.strip() for s in raw.split(',') if s.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
