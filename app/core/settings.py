from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Product Warranty Registration Portal"
    DATABASE_URL: str = "sqlite:///./warranty_portal.db"
    SECRET_KEY: str = "dev-secret-key-change-me"
    SESSION_COOKIE: str = "warranty_session"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
