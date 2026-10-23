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

    respx.get(_OPENFOOTBALL_URL).mock(return_value=Response(200, json=_load("worldcup.json")))
    result = await OpenFootballFixturesAdapter().fetch()
    played = result["fixtures"][0]
    assert played["home"] == "Mexico"
    assert played["away"] == "South Africa"
    assert played["stage"] == "Matchday 1"
    # Decided matches carry the winner NAME (opus cook6 T6.1); None only when level.
    assert played["winner"] == "Mexico"
    assert played["status"] == "FINISHED"
    assert played["home_goals"] == 2
    assert played["away_goals"] == 0


@respx.mock
async def test_unplayed_match_is_scheduled_with_null_goals():
    from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter

    respx.get(_OPENFOOTBALL_URL).mock(return_value=Response(200, json=_load("worldcup.json")))
    result = await OpenFootballFixturesAdapter().fetch()
    upcoming = result["fixtures"][1]
    assert upcoming["status"] == "SCHEDULED"
    assert upcoming["home_goals"] is None
    assert upcoming["away_goals"] is None


@respx.mock
async def test_fixtures_shape_matches_chain_contract():
    # Discipline: fallback adapters in a chain return the SAME keys.
    from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter

    respx.get(_OPENFOOTBALL_URL).mock(return_value=Response(200, json=_load("worldcup.json")))
    result = await OpenFootballFixturesAdapter().fetch()
    assert set(result["fixtures"][0]) >= {"home", "away", "status", "home_goals", "away_goals"}


@respx.mock
async def test_empty_matches_raises_not_found():
    import pytest

    from sportiq.core.errors import NotFoundError
    from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter

    respx.get(_OPENFOOTBALL_URL).mock(return_value=Response(200, json={"matches": []}))
    with pytest.raises(NotFoundError):
        await OpenFootballFixturesAdapter().fetch()


@respx.mock
async def test_openfootball_adapter_sets_winner_from_extra_time():
    from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter

    respx.get(_OPENFOOTBALL_URL).mock(return_value=Response(200, json=_load("worldcup.json")))
    result = await OpenFootballFixturesAdapter().fetch()
    final = result["fixtures"][2]  # ft [0,0], et [1,0]
    assert final["winner"] == "Spain"
    assert final["home_goals"] == 1
    assert final["away_goals"] == 0
    assert final["regulation_home_goals"] == 0
    assert final["penalties_home"] is None
    assert final["status"] == "FINISHED"


@respx.mock
async def test_openfootball_adapter_sets_winner_from_penalties():
    from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter

    respx.get(_OPENFOOTBALL_URL).mock(return_value=Response(200, json=_load("worldcup.json")))
    result = await OpenFootballFixturesAdapter().fetch()
    shootout = result["fixtures"][3]  # ft/et [1,1], p [3,4]
    assert shootout["winner"] == "Paraguay"
    assert (shootout["home_goals"], shootout["away_goals"]) == (1, 1)
    assert (shootout["penalties_home"], shootout["penalties_away"]) == (3, 4)


@respx.mock
async def test_openfootball_adapter_group_draw_has_no_winner():
    from sportiq.football.adapters.openfootball import OpenFootballFixturesAdapter

    respx.get(_OPENFOOTBALL_URL).mock(return_value=Response(200, json=_load("worldcup.json")))
    result = await OpenFootballFixturesAdapter().fetch()
    draw = result["fixtures"][4]  # group match ft [1,1]
    assert draw["winner"] is None
    assert draw["status"] == "FINISHED"
