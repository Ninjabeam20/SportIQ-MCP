"""Cricbuzz scraper adapter tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.core.errors import MissingCredentialsError
from sportiq.cricket.adapters.cricbuzz_scraper import CricbuzzLiveMatchesAdapter

_HTML = (Path(__file__).parent.parent / "fixtures" / "cricbuzz" / "live_page.html").read_text()


async def test_raises_when_disabled(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.enable_cricbuzz_scraper", False)
    adapter = CricbuzzLiveMatchesAdapter()
    with pytest.raises(MissingCredentialsError):
        await adapter.fetch()


async def test_healthcheck_false_when_disabled(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.enable_cricbuzz_scraper", False)
    assert await CricbuzzLiveMatchesAdapter().healthcheck() is False


async def test_healthcheck_true_when_enabled(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.enable_cricbuzz_scraper", True)
    assert await CricbuzzLiveMatchesAdapter().healthcheck() is True


@respx.mock
async def test_parses_live_matches_from_html(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.enable_cricbuzz_scraper", True)
    respx.get("https://m.cricbuzz.com/cricket-match/live-scores").mock(
        return_value=Response(200, text=_HTML)
    )
    adapter = CricbuzzLiveMatchesAdapter()
    result = await adapter.fetch()
    assert "matches" in result
    assert isinstance(result["matches"], list)
