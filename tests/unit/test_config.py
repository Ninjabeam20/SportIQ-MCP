

def test_enable_ndtv_scraper_via_documented_env_var(monkeypatch):
    """Test that SPORTIQ_ENABLE_NDTV=1 correctly sets enable_ndtv_scraper."""
    monkeypatch.setenv("SPORTIQ_ENABLE_NDTV", "1")
    # Import a fresh Settings instance (not the module-level singleton)
    from sportiq.config import Settings

    s = Settings()
    assert s.enable_ndtv_scraper is True


def test_enable_cricbuzz_scraper_via_documented_env_var(monkeypatch):
    """Test that SPORTIQ_ENABLE_CRICBUZZ=1 correctly sets enable_cricbuzz_scraper."""
    monkeypatch.setenv("SPORTIQ_ENABLE_CRICBUZZ", "1")
    # Import a fresh Settings instance (not the module-level singleton)
    from sportiq.config import Settings

    s = Settings()
    assert s.enable_cricbuzz_scraper is True


def test_log_format_defaults_json_on_cloud_run(monkeypatch):
    """Cloud Run sets K_SERVICE; logs must default to JSON there so Cloud Logging
    parses them into jsonPayload (the dashboard filters on jsonPayload.event)."""
    monkeypatch.delenv("SPORTIQ_LOG_FORMAT", raising=False)
    monkeypatch.setenv("K_SERVICE", "sportiq-mcp")
    from sportiq.config import Settings

    s = Settings(_env_file=None)
    assert s.sportiq_log_format == "json"


def test_log_format_defaults_pretty_locally(monkeypatch):
    """Without K_SERVICE (local dev) logs default to the pretty console renderer."""
    monkeypatch.delenv("SPORTIQ_LOG_FORMAT", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)
    from sportiq.config import Settings

    s = Settings(_env_file=None)
    assert s.sportiq_log_format == "pretty"


def test_explicit_log_format_overrides_cloud_run_default(monkeypatch):
    """An explicit SPORTIQ_LOG_FORMAT wins even on Cloud Run."""
    monkeypatch.setenv("K_SERVICE", "sportiq-mcp")
    monkeypatch.setenv("SPORTIQ_LOG_FORMAT", "pretty")
    from sportiq.config import Settings

    s = Settings(_env_file=None)
    assert s.sportiq_log_format == "pretty"


def test_blank_scraper_toggle_is_off_not_crash(monkeypatch):
    """A present-but-blank toggle (`SPORTIQ_ENABLE_NDTV=`) must coerce to False,
    not raise. The built-in dotenv parser passes '' through and '' is not a valid
    bool, so without the validator this would crash startup."""
    monkeypatch.setenv("SPORTIQ_ENABLE_NDTV", "")
    monkeypatch.setenv("SPORTIQ_ENABLE_CRICBUZZ", "")
    from sportiq.config import Settings

    s = Settings()
    assert s.enable_ndtv_scraper is False
    assert s.enable_cricbuzz_scraper is False
