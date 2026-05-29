"""football-data.org adapters (v4).

Free tier: 10 req/min, 100/day. Token (FOOTBALLDATA_KEY) is OPTIONAL — the
public tier works without it (it just rate-limits harder), so the constructor
never raises on a missing key. Outputs are normalised to the common per-chain
shapes (see base.py).
"""
from __future__ import annotations

from sportiq.config import settings
from sportiq.core.http import get_json
from sportiq.core.ratelimit import Budget
from sportiq.football.adapters.base import _FD_COMPETITION, _FOOTBALLDATA_BASE

_FOOTBALLDATA_BUDGET = Budget(source="football_data_org", per_minute=10, per_day=100)


def _headers() -> dict:
    # Token is optional; send it only when present.
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
            score = match.get("score", {}).get("fullTime", {})
            fixtures.append(
                {
                    "home": match.get("homeTeam", {}).get("name"),
                    "away": match.get("awayTeam", {}).get("name"),
                    "date": match.get("utcDate"),
                    "status": match.get("status"),
                    "home_goals": score.get("home"),
                    "away_goals": score.get("away"),
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
