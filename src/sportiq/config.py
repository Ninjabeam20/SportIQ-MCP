import os
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_log_format() -> Literal["pretty", "json"]:
    """Default to JSON logs on Cloud Run, pretty locally.

    Cloud Run always sets ``K_SERVICE``. Emitting JSON there lets Cloud Logging
    parse each line into ``jsonPayload`` (so the analytics dashboard can filter on
    ``jsonPayload.event``); the ANSI ConsoleRenderer would land as opaque
    ``textPayload``. An explicit ``SPORTIQ_LOG_FORMAT`` env var still overrides this.
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

    # V1 pro-entitlement gate (honor-system): any non-blank value unlocks the 24
    # intel tools. Provider-agnostic — a key from Polar/LS/Paddle/Gumroad all work.
    # Real validation lands in V2; see docs/wiki/decisions/pro-entitlement-gate.md.
    sportiq_pro_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SPORTIQ_PRO_KEY", "sportiq_pro_key"),
    )

    # V2a hosted enforcement: comma-separated set of valid Pro keys. Set as a
    # Cloud Run secret on the host → the gate validates the per-request key
    # against this set instead of the V1 presence check. Unset (local stdio/uvx)
    # → presence check only (local is uncrackable open-source anyway). V2b swaps
    # this for a keystore filled by the GitHub sponsorship webhook.
    sportiq_valid_keys: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SPORTIQ_VALID_KEYS", "sportiq_valid_keys"),
    )

    # Hosted-demo hook: comma-separated tool names to keep FREE even though they
    # are in PAID_TOOLS. The host sets this (e.g. `football_simulate_bracket`) to
    # keep one flagship open as the World Cup discovery funnel; unset on PyPI so
    # local installs stay fully gated. Per-surface gating with one env var — no
    # code fork, no change to PAID_TOOLS.
    sportiq_free_tools: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SPORTIQ_FREE_TOOLS", "sportiq_free_tools"),
    )

    redis_url: str | None = None

    sportiq_log_level: str = "INFO"
    sportiq_log_format: Literal["pretty", "json"] = Field(default_factory=_default_log_format)

    diskcache_dir: Path = Path.home() / ".cache" / "sportiq"

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

    @field_validator(
        "sportiq_pro_key", "sportiq_valid_keys", "sportiq_free_tools", mode="before"
    )
    @classmethod
    def _blank_key_is_unset(cls, v: object) -> object:
        """Treat a present-but-blank key var (``SPORTIQ_PRO_KEY=`` /
        ``SPORTIQ_VALID_KEYS=``) as unset (not a key / not configured).

        A blank value left in a client config must not unlock the paid tools.
        Blank/whitespace → None; everything else passes through. ``get_active_key``
        re-applies the same guard at runtime so a value set after construction
        (tests, V2 contextvars) is held to the same rule.
        """
        if isinstance(v, str) and v.strip() == "":
            return None
        return v


settings = Settings()
