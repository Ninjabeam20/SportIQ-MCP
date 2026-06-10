"""RapidAPI Cricbuzz adapter tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.core.errors import MissingCredentialsError
from sportiq.cricket.adapters.rapidapi_cricbuzz import (
    RapidAPICricbuzzLiveAdapter,
    RapidAPICricbuzzPlayerStatsAdapter,
    RapidAPICricbuzzScorecardAdapter,
)

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


@respx.mock
async def test_scorecard_adapter_quotes_path_traversal_in_match_id(monkeypatch):
    """User-supplied ids are interpolated into the URL path; `../` sequences must
    be percent-encoded so a hostile id can't redirect the request to a different
    endpoint on the API host."""
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", "test_rapidapi_key")
    route = respx.get(host="cricbuzz-cricket.p.rapidapi.com").mock(
        return_value=Response(200, json={})
    )
    adapter = RapidAPICricbuzzScorecardAdapter()
    await adapter.fetch(match_id="../../stats/v1/x")
    # raw_path is the wire-level request target (url.path would show it decoded).
    raw_path = route.calls.last.request.url.raw_path
    assert raw_path.startswith(b"/mcenter/v1/")
    assert b"/stats/" not in raw_path


async def test_scorecard_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", None)
    adapter = RapidAPICricbuzzScorecardAdapter()
    with pytest.raises(MissingCredentialsError):
        await adapter.fetch(match_id="12345")


@respx.mock
async def test_player_stats_adapter_fetches_career(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", "test_rapidapi_key")
    fixture = _load("player_career.json")
    respx.get(
        "https://cricbuzz-cricket.p.rapidapi.com/stats/v1/player/1413/career"
    ).mock(return_value=Response(200, json=fixture))
    adapter = RapidAPICricbuzzPlayerStatsAdapter()
    result = await adapter.fetch(player_id="1413")
    assert "values" in result
    t20i = next(v for v in result["values"] if v["name"] == "T20I")
    assert t20i["runs"] == "4008"


async def test_player_stats_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.rapidapi_key", None)
    adapter = RapidAPICricbuzzPlayerStatsAdapter()
    with pytest.raises(MissingCredentialsError):
        await adapter.fetch(player_id="1413")
