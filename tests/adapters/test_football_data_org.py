"""football-data.org adapter tests — all HTTP mocked with respx."""
from __future__ import annotations

import json
from pathlib import Path

import respx
from httpx import Response

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "football_data_org"
_BASE = "https://api.football-data.org/v4"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


@respx.mock
async def test_fixtures_adapter_normalises_shape():
    from sportiq.football.adapters.football_data_org import FootballDataOrgFixturesAdapter

    respx.get(f"{_BASE}/competitions/WC/matches").mock(
        return_value=Response(200, json=_load("matches.json"))
    )
    result = await FootballDataOrgFixturesAdapter().fetch()
    assert result["fixtures"][0]["home"] == "Argentina"
    assert result["fixtures"][0]["away"] == "Mexico"
    assert result["fixtures"][0]["status"] == "SCHEDULED"


@respx.mock
async def test_standings_adapter_flattens_groups():
    from sportiq.football.adapters.football_data_org import FootballDataOrgStandingsAdapter

    respx.get(f"{_BASE}/competitions/WC/standings").mock(
        return_value=Response(200, json=_load("standings.json"))
    )
    result = await FootballDataOrgStandingsAdapter().fetch()
    assert result["standings"][0]["team"] == "Argentina"
    assert result["standings"][0]["group"] == "GROUP_A"
    assert result["standings"][0]["points"] == 9


@respx.mock
async def test_scorers_adapter_shape():
    from sportiq.football.adapters.football_data_org import FootballDataOrgScorersAdapter

    respx.get(f"{_BASE}/competitions/WC/scorers").mock(
        return_value=Response(200, json=_load("scorers.json"))
    )
    result = await FootballDataOrgScorersAdapter().fetch()
    assert result["scorers"][0]["name"] == "K. Mbappe"
    assert result["scorers"][0]["goals"] == 6


async def test_fixtures_shape_matches_api_football():
    # Discipline: fallback adapters in a chain return the SAME keys.
    from sportiq.football.adapters.football_data_org import FootballDataOrgFixturesAdapter

    with respx.mock:
        respx.get(f"{_BASE}/competitions/WC/matches").mock(
            return_value=Response(200, json=_load("matches.json"))
        )
        result = await FootballDataOrgFixturesAdapter().fetch()
    assert set(result["fixtures"][0]) >= {"home", "away", "status", "home_goals", "away_goals"}


async def test_no_token_does_not_raise():
    # football-data.org token is optional — adapter must not require it.
    from sportiq.football.adapters.football_data_org import FootballDataOrgScorersAdapter

    with respx.mock:
        respx.get(f"{_BASE}/competitions/WC/scorers").mock(
            return_value=Response(200, json=_load("scorers.json"))
        )
        result = await FootballDataOrgScorersAdapter().fetch()
    assert "scorers" in result
