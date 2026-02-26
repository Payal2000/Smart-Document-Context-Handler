"""
Application configuration — loaded from environment variables.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "Smart Document Context Handler"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://sdch:sdch_pass@localhost:5432/sdch"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 3600  # 1 hour

    # OpenAI
    openai_api_key: Optional[str] = None

    # File storage
    upload_dir: str = "/tmp/sdch_uploads"
    max_file_size_mb: int = 50

    # Tier thresholds (tokens)
    tier1_max_tokens: int = 12_000
    tier2_max_tokens: int = 25_000
    tier3_max_tokens: int = 50_000

    # RAG
    rag_top_k: int = 10
    chunk_target_tokens: int = 512
    chunk_overlap_tokens: int = 50

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
