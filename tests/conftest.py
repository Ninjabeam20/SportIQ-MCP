"""Shared pytest fixtures.

The cache singleton is reset per-test to an isolated diskcache directory so
tests never share state and never touch a real Redis instance.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sportiq import config as config_module
from sportiq.core import cache as cache_module


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Force every test to use a fresh diskcache under tmp_path. No Redis."""
    monkeypatch.setattr(config_module.settings, "redis_url", None)
    monkeypatch.setattr(config_module.settings, "diskcache_dir", tmp_path / "cache")
    monkeypatch.setattr(cache_module, "_cache_singleton", None)
    yield
    monkeypatch.setattr(cache_module, "_cache_singleton", None)


@pytest.fixture(autouse=True)
def no_live_credentials(monkeypatch: pytest.MonkeyPatch):
    """Blank every credential + scraper toggle for the whole test session.

    No pytest test should ever depend on a real API key — adapters are exercised
    via respx/stubs. Some healthchecks (e.g. CricAPILiveMatchesAdapter) make a
    live HTTP call when their key is truthy, and ``settings`` loads the developer's
    ``.env``. Without this guard, a key present in ``.env`` causes the suite to hit
    the live upstream (quota burn + the "NEVER call live APIs in tests" rule).
    """
    for cred in (
        "cricapi_key",
        "apifootball_key",
        "footballdata_key",
        "rapidapi_key",
        "theodds_key",
    ):
        monkeypatch.setattr(config_module.settings, cred, None)
    monkeypatch.setattr(config_module.settings, "enable_cricbuzz_scraper", False)
    monkeypatch.setattr(config_module.settings, "enable_ndtv_scraper", False)
