"""Meta-test: verify the no_live_credentials fixture has blanked all API keys."""

from sportiq import config as config_module


def test_no_live_credentials_fixture_blanks_all_keys():
    """Assert that all credential fields are nulled by the autouse fixture."""
    # API key fields must be None
    assert config_module.settings.cricapi_key is None
    assert config_module.settings.apifootball_key is None
    assert config_module.settings.footballdata_key is None
    assert config_module.settings.rapidapi_key is None
    assert config_module.settings.theodds_key is None

    # Scraper toggles must be False
    assert config_module.settings.enable_cricbuzz_scraper is False
    assert config_module.settings.enable_ndtv_scraper is False
