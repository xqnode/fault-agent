from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "fault-agent"
    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:123456@localhost:5432/fault_agent"
    api_prefix: str = "/api"

    # Phase 2 simulator
    simulator_sample_interval_seconds: int = 10
    simulator_retention_days: int = 7
    simulator_debounce_n: int = 3

    # JWT
    jwt_secret: str = "fault-agent-dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 12


@lru_cache
def get_settings() -> Settings:
    return Settings()
