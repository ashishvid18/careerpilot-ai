
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"
    frontend_origin: str = "http://localhost:5173"

    jooble_api_key: str = ""
    jooble_api_base_url: str = "https://in.jooble.org/api"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()
