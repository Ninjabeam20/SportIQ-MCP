"""football-data.org adapters (v4).

Free tier: 10 req/min, 100/day. A token (FOOTBALLDATA_KEY) is required for the
World Cup competition — token-less ``/competitions/WC/matches`` returns HTTP 403
(the free tier includes the WC, but only once you register a free token). The
constructor still never raises on a missing key: without one the adapter simply
403s and the chain walks past it to the keyless openfootball / static-seed
fallbacks. Outputs are normalised to the common per-chain shapes (see base.py).
"""
from __future__ import annotations

from sportiq.config import settings
from sportiq.core.http import get_json
from sportiq.core.ratelimit import Budget
from sportiq.football.adapters.base import _FD_COMPETITION, _FOOTBALLDATA_BASE

_FOOTBALLDATA_BUDGET = Budget(source="football_data_org", per_minute=10, per_day=100)


def _headers() -> dict:
    # Send the token when present. The WC competition 403s without it, so a
    # missing key means this adapter fails and the chain falls through.
    return {"X-Auth-Token": settings.footballdata_key} if settings.footballdata_key else {}


class FootballDataOrgFixturesAdapter:
    name = "football_data_org"
    budget = _FOOTBALLDATA_BUDGET

    async def fetch(self, competition: str = _FD_COMPETITION, **kwargs) -> dict:
        data = await get_json(
            f"{_FOOTBALLDATA_BASE}/competitions/{competition}/matches",
            headers=_headers(),
        )
        fixtures = []
        for match in data.get("matches", []):
            home = match.get("homeTeam", {})
            away = match.get("awayTeam", {})
            score_block = match.get("score", {})
            score = score_block.get("fullTime", {})
            winner = {
                "HOME_TEAM": home.get("name"),
                "AWAY_TEAM": away.get("name"),
            }.get(score_block.get("winner"))
            fixtures.append(
                {
                    "match_id": match.get("id"),
                    "home": home.get("name"),
                    "away": away.get("name"),
                    "date": match.get("utcDate"),
                    "stage": match.get("stage"),
                    "status": match.get("status"),
                    "home_goals": score.get("home"),
                    "away_goals": score.get("away"),
                    "winner": winner,
                }
            )
        return {"fixtures": fixtures}

    async def healthcheck(self) -> bool:
        return True


class FootballDataOrgStandingsAdapter:
    name = "football_data_org"
    budget = _FOOTBALLDATA_BUDGET

    async def fetch(self, competition: str = _FD_COMPETITION, **kwargs) -> dict:
        data = await get_json(
            f"{_FOOTBALLDATA_BASE}/competitions/{competition}/standings",
            headers=_headers(),
        )
        standings = []
        for block in data.get("standings", []):
            group = block.get("group")
            for row in block.get("table", []):
                standings.append(
                    {
                        "rank": row.get("position"),
                        "team": row.get("team", {}).get("name"),
                        "group": group,
                        "points": row.get("points"),
                        "played": row.get("playedGames"),
                        "goals_diff": row.get("goalDifference"),
                    }
                )
        return {"standings": standings}

    async def healthcheck(self) -> bool:
        return True


class FootballDataOrgTeamStatsAdapter:
    name = "football_data_org"
    budget = _FOOTBALLDATA_BUDGET

    async def fetch(self, team: int, **kwargs) -> dict:
        data = await get_json(f"{_FOOTBALLDATA_BASE}/teams/{team}", headers=_headers())
        return {
            "team_stats": {
                "team": data.get("name"),
                "played": None,
                "wins": None,
                "goals_for": None,
                "goals_against": None,
            }
        }

    async def healthcheck(self) -> bool:
        return True


class FootballDataOrgScorersAdapter:
    name = "football_data_org"
    budget = _FOOTBALLDATA_BUDGET

    async def fetch(self, competition: str = _FD_COMPETITION, **kwargs) -> dict:
        data = await get_json(
            f"{_FOOTBALLDATA_BASE}/competitions/{competition}/scorers",
            headers=_headers(),
        )
        scorers = []
        for item in data.get("scorers", []):
            scorers.append(
                {
                    "name": item.get("player", {}).get("name"),
                    "team": item.get("team", {}).get("name"),
                    "goals": item.get("goals"),
                    "assists": item.get("assists"),
                }
            )
        return {"scorers": scorers}

    async def healthcheck(self) -> bool:
        return True
