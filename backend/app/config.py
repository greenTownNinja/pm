from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
STATIC_DIR = BACKEND_DIR / "static"


class Settings(BaseSettings):
    """Configuration, read from the environment or the project root .env."""

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    openrouter_api_key: str = ""
    session_secret: str = "dev-secret-change-me"


settings = Settings()
