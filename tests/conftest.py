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
