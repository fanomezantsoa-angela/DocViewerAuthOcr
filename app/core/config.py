# app/core/config.py
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str = Field("sqlite:///./app.db", alias="DATABASE_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
