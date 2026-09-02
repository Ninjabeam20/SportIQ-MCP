import os
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_log_format() -> Literal["pretty", "json"]:
    """Default to JSON logs when ``K_SERVICE`` is set (historical Cloud Run), pretty locally.

    The Dell Compose stack must not set ``K_SERVICE``; it sets ``SPORTIQ_LOG_FORMAT=json``
    instead so docker json-file / the JSONL dashboard can parse events. An explicit
    ``SPORTIQ_LOG_FORMAT`` env var still overrides this default.
    """
    return "json" if os.getenv("K_SERVICE") else "pretty"


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

    # Opt-in: walk the frozen football Elo seed forward from completed WC matches
    # so unplayed-match probabilities and the single-match predictors reflect form.
    # Off by default — does not re-tune the seed lineage (see D1 finding).
    football_live_elo: bool = Field(
        default=False,
        validation_alias=AliasChoices("SPORTIQ_FOOTBALL_LIVE_ELO", "football_live_elo"),
    )

    redis_url: str | None = None

    http_max_body_bytes: int = Field(default=1_048_576, gt=0)
    http_rate_limit_per_minute: int = Field(default=60, gt=0)
    http_global_rate_limit_per_minute: int = Field(default=300, gt=0)
    expensive_tool_concurrency: int = Field(default=2, gt=0)

    sportiq_log_level: str = "INFO"
    sportiq_log_format: Literal["pretty", "json"] = Field(default_factory=_default_log_format)
    # Opt-in JSONL of tool_call / mcp_request lines for the local dashboard
    # after Cloud Logging is gone. Compose sets this on the Dell.
    sportiq_analytics_jsonl: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("SPORTIQ_ANALYTICS_JSONL", "sportiq_analytics_jsonl"),
    )

    diskcache_dir: Path = Path.home() / ".cache" / "sportiq"

    @field_validator("sportiq_analytics_jsonl", mode="before")
    @classmethod
    def _blank_path_is_none(cls, v: object) -> object:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        return v

    @field_validator(
        "enable_cricbuzz_scraper", "enable_ndtv_scraper", "football_live_elo", mode="before"
    )
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
