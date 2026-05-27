"""RapidAPI Cricbuzz adapter tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.cricket.adapters.rapidapi_cricbuzz import (
    RapidAPICricbuzzLiveAdapter,
    RapidAPICricbuzzScorecardAdapter,
)
from sportiq.core.errors import MissingCredentialsError

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "rapidapi"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


async def test_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", None)
    adapter = RapidAPICricbuzzLiveAdapter()
    with pytest.raises(MissingCredentialsError):
        await adapter.fetch()


async def test_healthcheck_false_when_key_missing(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", None)
    assert await RapidAPICricbuzzLiveAdapter().healthcheck() is False


async def test_healthcheck_true_when_key_set(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", "test_rapidapi_key")
    assert await RapidAPICricbuzzLiveAdapter().healthcheck() is True


@respx.mock
async def test_parses_live_matches(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", "test_rapidapi_key")
    fixture = _load("live_matches.json")
    respx.get("https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = RapidAPICricbuzzLiveAdapter()
    result = await adapter.fetch()
    assert "matches" in result
    assert len(result["matches"]) == 1
    assert result["matches"][0]["matchDesc"] == "1st T20I"


@respx.mock
async def test_scorecard_adapter_fetches_by_id(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", "test_rapidapi_key")
    fixture = _load("scorecard.json")
    respx.get("https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/12345/scard").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = RapidAPICricbuzzScorecardAdapter()
    result = await adapter.fetch(match_id="12345")
    assert result["matchHeader"]["matchId"] == 12345
    assert result["scorecard"][0]["scoreDetails"]["runs"] == 182


async def test_scorecard_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", None)
    adapter = RapidAPICricbuzzScorecardAdapter()
    with pytest.raises(MissingCredentialsError):
        await adapter.fetch(match_id="12345")
