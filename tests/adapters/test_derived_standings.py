"""derived_standings adapter tests — keyless, openfootball HTTP mocked with respx."""
from __future__ import annotations

import respx
from httpx import Response

from sportiq.football.adapters.derived_standings import DerivedStandingsAdapter
from sportiq.football.adapters.openfootball import _OPENFOOTBALL_URL
from sportiq.football.adapters.static_seed import load_wc2026

# Two teams from the shipped draw's Group A (derived, not hardcoded, so a
# draw-data regen from live sources cannot silently break this test).
_WC = load_wc2026()
_WINNER, _LOSER = (_WC["teams"][c]["name"] for c in _WC["groups"]["A"][:2])

_PAYLOAD = {
    "matches": [
        {
            "date": "2026-06-12",
            "team1": _WINNER,
            "team2": _LOSER,
            "score": {"ft": [2, 0]},
            "group": "Group A",
        }
    ]
}


@respx.mock
async def test_derived_standings_from_openfootball_results():
    respx.get(_OPENFOOTBALL_URL).mock(return_value=Response(200, json=_PAYLOAD))
    out = await DerivedStandingsAdapter().fetch()

    assert out["source"] == "derived_standings"
    group_a = [r for r in out["standings"] if r["group"] == "A"]
    top = group_a[0]
    assert top["team"] == _WINNER
    assert top["points"] == 3
    assert top["played"] == 1
    assert top["goals_diff"] == 2


@respx.mock
async def test_derived_standings_healthcheck_true():
    assert await DerivedStandingsAdapter().healthcheck() is True
