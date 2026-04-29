from __future__ import annotations

import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # SECRET_KEY: in production set via .env. The fallback uses a per-process
    # random value so the app does not start with a known/hardcoded key.
    # WARNING: with the random fallback, all sessions are invalidated on restart.
    # install.sh writes a stable key into /opt/sysintro/.env.
    SECRET_KEY: str = secrets.token_hex(32)
    DATABASE_URL: str = "sqlite:///./data/sysintro.db"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 240  # 4 hours
    SECURE_COOKIES: int = 0  # 0=False, 1=True
    DEBUG: int = 0  # secure default; install.sh writes 0 explicitly
    CORS_ORIGINS: str = "http://localhost:8000"
    ALGORITHM: str = "HS256"
    UPLOAD_DIR: str = "attachments"
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024  # 25 MB
    # Tightened: removed text/plain (XSS risk via .html named files) and msword
    # variants we don't actively use. PDF + Office formats only.
    ALLOWED_MIME_TYPES: list[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]


settings = Settings()
