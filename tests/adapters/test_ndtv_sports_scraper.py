"""NDTV Sports scraper adapter tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.cricket.adapters.ndtv_sports_scraper import NDTVLiveMatchesAdapter
from sportiq.core.errors import MissingCredentialsError

_HTML = (Path(__file__).parent.parent / "fixtures" / "ndtv_sports" / "live_page.html").read_text()


async def test_raises_when_disabled(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.enable_ndtv_scraper", False)
    adapter = NDTVLiveMatchesAdapter()
    with pytest.raises(MissingCredentialsError):
        await adapter.fetch()


async def test_healthcheck_false_when_disabled(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.enable_ndtv_scraper", False)
    assert await NDTVLiveMatchesAdapter().healthcheck() is False


async def test_healthcheck_true_when_enabled(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.enable_ndtv_scraper", True)
    assert await NDTVLiveMatchesAdapter().healthcheck() is True


@respx.mock
async def test_parses_live_matches_from_html(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.enable_ndtv_scraper", True)
    respx.get("https://sports.ndtv.com/cricket/live-scores").mock(
        return_value=Response(200, text=_HTML)
    )
    adapter = NDTVLiveMatchesAdapter()
    result = await adapter.fetch()
    assert "matches" in result
    assert isinstance(result["matches"], list)
