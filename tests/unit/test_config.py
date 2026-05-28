

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
