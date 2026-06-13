"""openfootball adapter — keyless, public-domain WC 2026 fixtures + results.

openfootball/worldcup.json ships the full World Cup 2026 fixture list as a
public-domain JSON file on GitHub, with real final scores filled in as matches
are played. No API key, no quota (``budget = None``) — so it slots in above the
static seed as the keyless source of real results when api-football /
football-data.org are unkeyed.

Caveat: the upstream is hand-updated (~once/day), so scores can lag several
hours behind kickoff. Wherever ``FOOTBALLDATA_KEY`` is set, the official
football-data.org adapter runs first and serves fresher scores.

Output is normalised to the common fixtures shape (see base.py).
"""
from __future__ import annotations

from sportiq.core.http import get_json

_OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
)


class OpenFootballFixturesAdapter:
    name = "openfootball"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        data = await get_json(_OPENFOOTBALL_URL)
        fixtures = []
        for match in data.get("matches", []):
            ft = (match.get("score") or {}).get("ft")
            played = isinstance(ft, list) and len(ft) == 2
            fixtures.append(
                {
                    "home": match.get("team1"),
                    "away": match.get("team2"),
                    "date": match.get("date"),
                    "group": match.get("group"),
                    "status": "FINISHED" if played else "SCHEDULED",
                    "home_goals": ft[0] if played else None,
                    "away_goals": ft[1] if played else None,
                }
            )
        return {"fixtures": fixtures}

    async def healthcheck(self) -> bool:
        return True
