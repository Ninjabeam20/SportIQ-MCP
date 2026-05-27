"""CricAPI adapter tests — all HTTP mocked with respx."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.cricket.adapters.cricapi import (
    CricAPILiveMatchesAdapter,
    CricAPIPointsTableAdapter,
    CricAPIScheduleAdapter,
    CricAPIScorecardAdapter,
    CricAPISquadAdapter,
)
from sportiq.core.errors import MissingCredentialsError

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "cricapi"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def set_cricapi_key(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.cricapi_key", "test_key")


@respx.mock
async def test_live_matches_adapter_parses_matches():
    fixture = _load("current_matches.json")
    respx.get("https://api.cricapi.com/v1/currentMatches").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPILiveMatchesAdapter()
    result = await adapter.fetch()
    assert "matches" in result
    assert len(result["matches"]) == 2
    assert result["matches"][0]["id"] == "abc123"


@respx.mock
async def test_live_matches_adapter_returns_empty_list_off_season():
    respx.get("https://api.cricapi.com/v1/currentMatches").mock(
        return_value=Response(200, json={"status": "success", "data": []})
    )
    adapter = CricAPILiveMatchesAdapter()
    result = await adapter.fetch()
    assert result == {"matches": []}


@respx.mock
async def test_schedule_adapter_parses_matches():
    fixture = _load("schedule.json")
    respx.get("https://api.cricapi.com/v1/matches").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPIScheduleAdapter()
    result = await adapter.fetch()
    assert "matches" in result
    assert len(result["matches"]) == 2


@respx.mock
async def test_squad_adapter_parses_squad():
    fixture = _load("squad.json")
    respx.get("https://api.cricapi.com/v1/series_squad").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPISquadAdapter()
    result = await adapter.fetch(series_id="series001")
    assert result["data"]["squad"][0]["team"] == "Mumbai Indians"


@respx.mock
async def test_scorecard_adapter_fetches_by_id():
    fixture = _load("match_scorecard.json")
    respx.get("https://api.cricapi.com/v1/match_scorecard").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPIScorecardAdapter()
    result = await adapter.fetch(match_id="abc123")
    assert result["data"]["id"] == "abc123"
    assert result["status"] == "success"


@respx.mock
async def test_points_table_adapter_parses_standings():
    fixture = _load("points_table.json")
    respx.get("https://api.cricapi.com/v1/series_points_table").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPIPointsTableAdapter()
    result = await adapter.fetch(series_id="ipl2026")
    assert result["data"]["pointsTable"][0]["team"] == "CSK"


async def test_live_matches_adapter_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.cricapi_key", None)
    adapter = CricAPILiveMatchesAdapter()
    with pytest.raises(MissingCredentialsError):
        await adapter.fetch()


async def test_healthcheck_false_when_key_missing(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.cricapi_key", None)
    adapter = CricAPILiveMatchesAdapter()
    assert await adapter.healthcheck() is False
