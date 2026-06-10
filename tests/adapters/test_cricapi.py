"""CricAPI adapter tests — all HTTP mocked with respx."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.core.errors import MissingCredentialsError, NotFoundError
from sportiq.cricket.adapters.cricapi import (
    CricAPILiveMatchesAdapter,
    CricAPIPlayerInfoAdapter,
    CricAPIPointsTableAdapter,
    CricAPIScheduleAdapter,
    CricAPIScorecardAdapter,
    CricAPISquadAdapter,
)

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
async def test_live_matches_adapter_raises_not_found_on_failure_envelope():
    """A CricAPI failure envelope (status != success, e.g. quota exhausted) must
    raise so the chain walks to NDTV/Cricbuzz/RapidAPI — NOT return an empty
    "success" that gets cached and shadows every fallback adapter."""
    respx.get("https://api.cricapi.com/v1/currentMatches").mock(
        return_value=Response(
            200, json={"apikey": "test_key", "status": "failure", "reason": "hits today exceeded"}
        )
    )
    adapter = CricAPILiveMatchesAdapter()
    with pytest.raises(NotFoundError):
        await adapter.fetch()


@respx.mock
async def test_schedule_adapter_raises_not_found_on_failure_envelope():
    """Same contract as live matches: a failure envelope must not become an
    empty cached success."""
    respx.get("https://api.cricapi.com/v1/matches").mock(
        return_value=Response(
            200, json={"apikey": "test_key", "status": "failure", "reason": "hits today exceeded"}
        )
    )
    adapter = CricAPIScheduleAdapter()
    with pytest.raises(NotFoundError):
        await adapter.fetch()


@respx.mock
async def test_live_matches_healthcheck_makes_no_http_call():
    """healthcheck() must be a key-presence check only. A live API call here
    burns CricAPI quota (100/day) every time sportiq_health() runs — and the
    hosted endpoint lets anyone call that."""
    adapter = CricAPILiveMatchesAdapter()
    assert await adapter.healthcheck() is True
    assert len(respx.calls) == 0


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
    # Normalised shape: {"players": [...], "team": ..., "source": "cricapi"}
    assert result["source"] == "cricapi"
    assert result["team"] == "Mumbai Indians"
    assert len(result["players"]) == 5
    assert result["players"][0]["name"] == "Rohit Sharma"
    assert result["players"][0]["role"] == "BAT"
    assert result["players"][0]["team"] == "Mumbai Indians"


@respx.mock
async def test_squad_adapter_parses_live_list_shape():
    """Live CricAPI series_squad returns ``data`` as a LIST of {teamName, players}
    blocks, not ``data.squad``. The adapter must parse that real shape without
    raising (regression: it crashed with `'list' object has no attribute 'get'`).
    """
    fixture = _load("squad_live.json")
    respx.get("https://api.cricapi.com/v1/series_squad").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPISquadAdapter()
    result = await adapter.fetch(series_id="series001")
    assert result["source"] == "cricapi"
    assert len(result["players"]) == 7  # 5 MI + 2 CSK, flattened
    assert result["players"][0]["name"] == "Rohit Sharma"
    assert result["players"][0]["team"] == "Mumbai Indians"
    assert result["team"] == "Mumbai Indians"


@respx.mock
async def test_squad_adapter_live_shape_empty_list():
    """An empty-but-successful series_squad (squads not yet announced) returns
    ``data: []`` — must yield an empty squad, not raise."""
    respx.get("https://api.cricapi.com/v1/series_squad").mock(
        return_value=Response(200, json={"status": "success", "data": []})
    )
    adapter = CricAPISquadAdapter()
    result = await adapter.fetch(series_id="series001")
    assert result["players"] == []
    assert result["source"] == "cricapi"


@respx.mock
async def test_squad_adapter_filters_by_team():
    """team= kwarg keeps only the matching block from the series payload."""
    fixture = _load("squad.json")
    respx.get("https://api.cricapi.com/v1/series_squad").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPISquadAdapter()
    result = await adapter.fetch(series_id="series001", team="mumbai")
    assert all(p["team"] == "Mumbai Indians" for p in result["players"])


async def test_squad_adapter_raises_without_series_id():
    """No series_id → raise NotFoundError so the chain falls through to the
    static_seed terminator, rather than querying CricAPI with id=None and
    caching the empty failure result (which shadowed the seed roster)."""
    adapter = CricAPISquadAdapter()
    with pytest.raises(NotFoundError):
        await adapter.fetch(series_id=None, team="MI")


@respx.mock
async def test_scorecard_adapter_fetches_by_id():
    fixture = _load("match_scorecard.json")
    respx.get("https://api.cricapi.com/v1/match_scorecard").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPIScorecardAdapter()
    result = await adapter.fetch(match_id="abc123")
    # Unwrapped to inner data; the request apikey never reaches tool output.
    assert result["id"] == "abc123"
    assert "apikey" not in result


@respx.mock
async def test_scorecard_adapter_raises_not_found_on_failure_envelope():
    """A CricAPI failure envelope (status != success) must raise NotFoundError —
    never return the raw body, which echoes the request apikey."""
    fixture = _load("match_scorecard_failure.json")
    respx.get("https://api.cricapi.com/v1/match_scorecard").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPIScorecardAdapter()
    with pytest.raises(NotFoundError):
        await adapter.fetch(match_id="missing-id")


@respx.mock
async def test_points_table_adapter_parses_standings():
    fixture = _load("points_table.json")
    respx.get("https://api.cricapi.com/v1/series_points_table").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPIPointsTableAdapter()
    result = await adapter.fetch(series_id="ipl2026")
    assert result["pointsTable"][0]["team"] == "CSK"
    assert "apikey" not in result


async def test_live_matches_adapter_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.cricapi_key", None)
    adapter = CricAPILiveMatchesAdapter()
    with pytest.raises(MissingCredentialsError):
        await adapter.fetch()


async def test_healthcheck_false_when_key_missing(monkeypatch):
    monkeypatch.setattr("sportiq.config.settings.cricapi_key", None)
    adapter = CricAPILiveMatchesAdapter()
    assert await adapter.healthcheck() is False


@respx.mock
async def test_player_info_adapter_returns_profile_and_stats():
    fixture = _load("players_info.json")
    respx.get("https://api.cricapi.com/v1/players_info").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricAPIPlayerInfoAdapter()
    result = await adapter.fetch(player_id="p_kohli_001")
    assert result["id"] == "p_kohli_001"
    assert result["name"] == "Virat Kohli"
    assert "apikey" not in result
    t20i_runs = next(
        s for s in result["stats"]
        if s["matchtype"] == "t20i" and s["stat"] == "Runs"
    )
    assert t20i_runs["value"] == "4008"
