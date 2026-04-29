from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SECRET_KEY: str = "dev-secret-key-CHANGE_ME"
    DATABASE_URL: str = "sqlite:///./data/sysintro.db"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    SECURE_COOKIES: int = 0  # 0=False, 1=True
    DEBUG: int = 1
    CORS_ORIGINS: str = "http://localhost:8000"
    ALGORITHM: str = "HS256"
    UPLOAD_DIR: str = "attachments"
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024  # 25 MB
    ALLOWED_MIME_TYPES: list[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ]


settings = Settings()
