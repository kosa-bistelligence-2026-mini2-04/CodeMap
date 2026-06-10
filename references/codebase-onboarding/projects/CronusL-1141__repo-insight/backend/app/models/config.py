from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    openai_api_key: str = ""
    llm_model: str = "gpt-5.4"

    # GitHub (optional, for issue API)
    github_token: str = ""

    # Analysis budgets (seconds)
    budget_total_s: int = 120
    budget_static_s: int = 60
    budget_behavior_s: int = 50
    budget_community_s: int = 45
    budget_reporter_s: int = 30

    # Database
    sqlite_path: str = "./data/repo_insight.db"

    # Guardrail thresholds
    semantic_similarity_threshold: float = 0.35
    max_hallucination_ratio: float = 0.2

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # App
    app_version: str = "0.1.0"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
