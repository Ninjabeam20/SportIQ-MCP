"""API-Football adapter tests — all HTTP mocked with respx."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.config import settings

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "api_football"
_BASE = "https://v3.football.api-sports.io"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def _with_key(monkeypatch):
    monkeypatch.setattr(settings, "apifootball_key", "test-key")


@respx.mock
async def test_fixtures_adapter_normalises_shape():
    from sportiq.football.adapters.api_football import APIFootballFixturesAdapter

    respx.get(f"{_BASE}/fixtures").mock(return_value=Response(200, json=_load("fixtures.json")))
    result = await APIFootballFixturesAdapter().fetch()
    assert "fixtures" in result
    assert result["fixtures"][0]["home"] == "Mexico"
    assert result["fixtures"][0]["away"] == "Poland"


@respx.mock
async def test_standings_adapter_flattens_groups():
    from sportiq.football.adapters.api_football import APIFootballStandingsAdapter

    respx.get(f"{_BASE}/standings").mock(return_value=Response(200, json=_load("standings.json")))
    result = await APIFootballStandingsAdapter().fetch()
    assert result["standings"][0]["team"] == "Argentina"
    assert result["standings"][0]["points"] == 9


@respx.mock
async def test_team_stats_adapter_shape():
    from sportiq.football.adapters.api_football import APIFootballTeamStatsAdapter

    respx.get(f"{_BASE}/teams/statistics").mock(
        return_value=Response(200, json=_load("team_statistics.json"))
    )
    result = await APIFootballTeamStatsAdapter().fetch(team=26)
    assert result["team_stats"]["team"] == "Argentina"
    assert result["team_stats"]["goals_for"] == 7


@respx.mock
async def test_squad_adapter_shape():
    from sportiq.football.adapters.api_football import APIFootballSquadAdapter

    respx.get(f"{_BASE}/players/squads").mock(return_value=Response(200, json=_load("squads.json")))
    result = await APIFootballSquadAdapter().fetch(team=26)
    assert result["squad"][0]["name"] == "L. Messi"
    assert result["squad"][0]["number"] == 10


@respx.mock
async def test_scorers_adapter_shape():
    from sportiq.football.adapters.api_football import APIFootballScorersAdapter

    respx.get(f"{_BASE}/players/topscorers").mock(
        return_value=Response(200, json=_load("topscorers.json"))
    )
    result = await APIFootballScorersAdapter().fetch()
    assert result["scorers"][0]["name"] == "K. Mbappe"
    assert result["scorers"][0]["goals"] == 6


async def test_missing_key_raises_missing_credentials(monkeypatch):
    from sportiq.core.errors import MissingCredentialsError
    from sportiq.football.adapters.api_football import APIFootballFixturesAdapter

    monkeypatch.setattr(settings, "apifootball_key", None)
    with pytest.raises(MissingCredentialsError):
        await APIFootballFixturesAdapter().fetch()


async def test_healthcheck_false_without_key(monkeypatch):
    from sportiq.football.adapters.api_football import APIFootballFixturesAdapter

    monkeypatch.setattr(settings, "apifootball_key", None)
    assert await APIFootballFixturesAdapter().healthcheck() is False
