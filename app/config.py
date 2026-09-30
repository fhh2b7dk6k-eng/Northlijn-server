from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    """Loaded from environment variables (or a local .env file). See
    .env.example for the full list and what each one means."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    jwt_secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Render's auto-generated Postgres connection string (and most
        providers') comes as a bare `postgres://` or `postgresql://`, which
        makes SQLAlchemy default to the legacy psycopg2 dialect — not
        installed here, since this project uses psycopg3. Normalize it so
        deployment doesn't depend on remembering to edit the URL by hand."""
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://"):]
        return value


settings = Settings()
