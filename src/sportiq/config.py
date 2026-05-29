from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    cricapi_key: str | None = None
    apifootball_key: str | None = None
    footballdata_key: str | None = None  # optional higher tier for football-data.org
    rapidapi_key: str | None = None
    theodds_key: str | None = None  # the-odds-api.com — 500 req/month free; cricket + football odds

    enable_cricbuzz_scraper: bool = Field(
        default=False,
        validation_alias=AliasChoices("SPORTIQ_ENABLE_CRICBUZZ", "enable_cricbuzz_scraper"),
    )
    enable_ndtv_scraper: bool = Field(
        default=False,
        validation_alias=AliasChoices("SPORTIQ_ENABLE_NDTV", "enable_ndtv_scraper"),
    )

    redis_url: str | None = None

    sportiq_log_level: str = "INFO"
    sportiq_log_format: Literal["pretty", "json"] = "pretty"

    diskcache_dir: Path = Path.home() / ".cache" / "sportiq"

    @field_validator("enable_cricbuzz_scraper", "enable_ndtv_scraper", mode="before")
    @classmethod
    def _blank_toggle_is_off(cls, v: object) -> object:
        """Treat a present-but-blank env toggle (`SPORTIQ_ENABLE_NDTV=`) as off.

        The built-in pydantic-settings dotenv parser passes empty strings through
        rather than falling back to the default, and an empty string is not a
        valid bool — so without this the scrapers being left blank in .env would
        crash startup. Blank/whitespace → False; everything else parses normally.
        """
        if isinstance(v, str) and v.strip() == "":
            return False
        return v


settings = Settings()
