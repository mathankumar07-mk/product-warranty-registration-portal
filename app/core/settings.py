from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Product Warranty Registration Portal"
    DATABASE_URL: str | None = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "warranty_portal"
    POSTGRES_USER: str = "warranty_app"
    POSTGRES_PASSWORD: str | None = None
    SECRET_KEY: str = "dev-secret-key-change-me"
    SESSION_COOKIE: str = "warranty_session"
    CORS_ORIGINS: str = "http://localhost:3000"
    ENVIRONMENT: str = "development"
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_SECURE: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
