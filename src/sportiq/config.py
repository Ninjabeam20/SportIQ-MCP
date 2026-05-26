from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cricapi_key: str | None = None
    apifootball_key: str | None = None

    redis_url: str | None = None

    sportiq_log_level: str = "INFO"
    sportiq_log_format: Literal["pretty", "json"] = "pretty"

    diskcache_dir: Path = Path.home() / ".cache" / "sportiq"


settings = Settings()
