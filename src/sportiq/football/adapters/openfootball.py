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

from sportiq.core.errors import NotFoundError
from sportiq.core.http import get_json

_OPENFOOTBALL_URL = (
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
)


def _is_pair(value: object) -> bool:
    return isinstance(value, list) and len(value) == 2


def _winner(match: dict, final: list, pens: list | None) -> str | None:
    """Winning team NAME (football_data_org convention): penalties, then the final score.

    None only when the match is still level (e.g. a group-stage draw).
    """
    home, away = match.get("team1"), match.get("team2")
    for a, b in ((pens or [0, 0]), final):
        if a > b:
            return home
        if b > a:
            return away
    return None


class OpenFootballFixturesAdapter:
    name = "openfootball"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        data = await get_json(_OPENFOOTBALL_URL)
        matches = data.get("matches", [])
        if not matches:
            raise NotFoundError("openfootball returned no matches")
        fixtures = []
        for match in matches:
            score = match.get("score") or {}
            ft = score.get("ft")
            played = _is_pair(ft)
            et = score.get("et") if played and _is_pair(score.get("et")) else None
            pens = score.get("p") if played and _is_pair(score.get("p")) else None
            final = et or ft  # goals after extra time when it was played
            fixtures.append(
                {
                    "match_id": match.get("id"),
                    "home": match.get("team1"),
                    "away": match.get("team2"),
                    "date": match.get("date"),
                    "group": match.get("group"),
                    "stage": match.get("round"),
                    "status": "FINISHED" if played else "SCHEDULED",
                    "home_goals": final[0] if played else None,
                    "away_goals": final[1] if played else None,
                    "regulation_home_goals": ft[0] if played else None,
                    "regulation_away_goals": ft[1] if played else None,
                    "penalties_home": pens[0] if pens else None,
                    "penalties_away": pens[1] if pens else None,
                    "winner": _winner(match, final, pens) if played else None,
                }
            )
        return {"fixtures": fixtures}

    async def healthcheck(self) -> bool:
        return True
