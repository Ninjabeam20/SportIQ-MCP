"""openfootball adapter tests — all HTTP mocked with respx."""
from __future__ import annotations

import json
from pathlib import Path

import respx
from httpx import Response

from sportiq.football.adapters.openfootball import _OPENFOOTBALL_URL

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "openfootball"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


@respx.mock
async def test_finished_match_carries_real_score():
    from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter

    respx.get(_OPENFOOTBALL_URL).mock(
        return_value=Response(200, json=_load("worldcup.json"))
    )
    result = await OpenFootballFixturesAdapter().fetch()
    played = result["fixtures"][0]
    assert played["home"] == "Mexico"
    assert played["away"] == "South Africa"
    assert played["stage"] == "Matchday 1"
    assert played["winner"] is None
    assert played["status"] == "FINISHED"
    assert played["home_goals"] == 2
    assert played["away_goals"] == 0


@respx.mock
async def test_unplayed_match_is_scheduled_with_null_goals():
    from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter

    respx.get(_OPENFOOTBALL_URL).mock(
        return_value=Response(200, json=_load("worldcup.json"))
    )
    result = await OpenFootballFixturesAdapter().fetch()
    upcoming = result["fixtures"][1]
    assert upcoming["status"] == "SCHEDULED"
    assert upcoming["home_goals"] is None
    assert upcoming["away_goals"] is None


@respx.mock
async def test_fixtures_shape_matches_chain_contract():
    # Discipline: fallback adapters in a chain return the SAME keys.
    from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter

    respx.get(_OPENFOOTBALL_URL).mock(
        return_value=Response(200, json=_load("worldcup.json"))
    )
    result = await OpenFootballFixturesAdapter().fetch()
    assert set(result["fixtures"][0]) >= {"home", "away", "status", "home_goals", "away_goals"}
