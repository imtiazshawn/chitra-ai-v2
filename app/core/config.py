from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "ChitraAI"
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=True, alias="DEBUG")

    # Database
    database_url: SecretStr = Field(
        default=SecretStr("postgresql://localhost:5432/chitraai"),
        alias="DATABASE_URL",
    )

    # Redis & Celery
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        alias="CELERY_RESULT_BACKEND",
    )

    # AI & external API keys (free-tier providers)
    gemini_api_key: SecretStr = Field(default=SecretStr(""), alias="GEMINI_API_KEY")
    groq_api_key: SecretStr = Field(default=SecretStr(""), alias="GROQ_API_KEY")
    pexels_api_key: SecretStr = Field(default=SecretStr(""), alias="PEXELS_API_KEY")
    elevenlabs_api_key: SecretStr = Field(
        default=SecretStr(""),
        alias="ELEVENLABS_API_KEY",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
