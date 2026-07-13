"""API-Football adapters (v3.football.api-sports.io).

100 req/day free tier, shared across endpoints. Requires APIFOOTBALL_KEY;
raises MissingCredentialsError when absent so the chain walks past silently.
Each adapter normalises the provider's ``{"response": [...]}`` envelope into the
common per-chain output shape (see base.py).
"""
from __future__ import annotations

from sportiq.config import settings
from sportiq.core.errors import MissingCredentialsError, NotFoundError
from sportiq.core.http import get_json
from sportiq.core.ratelimit import Budget
from sportiq.football.adapters.base import _APIFOOTBALL_BASE, _WC_LEAGUE_ID, _WC_SEASON

# Shared per-source budget — the free tier counts every endpoint against 100/day.
_APIFOOTBALL_BUDGET = Budget(source="api_football", per_day=100)


def _headers() -> dict:
    if not settings.apifootball_key:
        raise MissingCredentialsError("APIFOOTBALL_KEY is not set")
    return {"x-apisports-key": settings.apifootball_key}


def _has_key() -> bool:
    return bool(settings.apifootball_key)


class APIFootballFixturesAdapter:
    name = "api_football"
    budget = _APIFOOTBALL_BUDGET

    async def fetch(self, league: int = _WC_LEAGUE_ID, season: int = _WC_SEASON, **kwargs) -> dict:
        data = await get_json(
            f"{_APIFOOTBALL_BASE}/fixtures",
            params={"league": league, "season": season},
            headers=_headers(),
        )
        # The free plan silently returns an empty response for seasons it does
        # not cover (e.g. WC 2026). An empty fixture list must NOT count as a
        # success — the chain would cache it for 30min and shadow the sources
        # below that do have the data. Raise so the chain walks on.
        if not data.get("response"):
            raise NotFoundError(
                f"api_football returned no fixtures for league={league} season={season}"
            )
        fixtures = []
        for item in data.get("response", []):
            fixture = item.get("fixture", {})
            league = item.get("league", {})
            teams = item.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("away", {})
            goals = item.get("goals", {})
            winner = None
            if home.get("winner") is True:
                winner = home.get("name")
            elif away.get("winner") is True:
                winner = away.get("name")
            fixtures.append(
                {
                    "match_id": fixture.get("id"),
                    "home": home.get("name"),
                    "away": away.get("name"),
                    "date": fixture.get("date"),
                    "stage": league.get("round"),
                    "status": fixture.get("status", {}).get("short"),
                    "home_goals": goals.get("home"),
                    "away_goals": goals.get("away"),
                    "winner": winner,
                }
            )
        return {"fixtures": fixtures}

    async def healthcheck(self) -> bool:
        return _has_key()


class APIFootballStandingsAdapter:
    name = "api_football"
    budget = _APIFOOTBALL_BUDGET

    async def fetch(self, league: int = _WC_LEAGUE_ID, season: int = _WC_SEASON, **kwargs) -> dict:
        data = await get_json(
            f"{_APIFOOTBALL_BASE}/standings",
            params={"league": league, "season": season},
            headers=_headers(),
        )
        standings = []
        response = data.get("response", [])
        if response:
            groups = response[0].get("league", {}).get("standings", [])
            for group in groups:
                for row in group:
                    team = row.get("team", {})
                    standings.append(
                        {
                            "rank": row.get("rank"),
                            "team": team.get("name"),
                            "group": row.get("group"),
                            "points": row.get("points"),
                            "played": row.get("all", {}).get("played"),
                            "goals_diff": row.get("goalsDiff"),
                        }
                    )
        return {"standings": standings}

    async def healthcheck(self) -> bool:
        return _has_key()


class APIFootballTeamStatsAdapter:
    name = "api_football"
    budget = _APIFOOTBALL_BUDGET

    async def fetch(
        self, team: int, league: int = _WC_LEAGUE_ID, season: int = _WC_SEASON, **kwargs
    ) -> dict:
        data = await get_json(
            f"{_APIFOOTBALL_BASE}/teams/statistics",
            params={"team": team, "league": league, "season": season},
            headers=_headers(),
        )
        resp = data.get("response", {}) or {}
        goals = resp.get("goals", {})
        return {
            "team_stats": {
                "team": resp.get("team", {}).get("name"),
                "played": resp.get("fixtures", {}).get("played", {}).get("total"),
                "wins": resp.get("fixtures", {}).get("wins", {}).get("total"),
                "goals_for": goals.get("for", {}).get("total", {}).get("total"),
                "goals_against": goals.get("against", {}).get("total", {}).get("total"),
            }
        }

    async def healthcheck(self) -> bool:
        return _has_key()


class APIFootballSquadAdapter:
    name = "api_football"
    budget = _APIFOOTBALL_BUDGET

    async def fetch(self, team: int, **kwargs) -> dict:
        data = await get_json(
            f"{_APIFOOTBALL_BASE}/players/squads",
            params={"team": team},
            headers=_headers(),
        )
        squad = []
        response = data.get("response", [])
        # An empty response means no squad for this arg (e.g. a country code was
        # passed where a numeric id is expected). Treat it as a miss so the chain
        # walks past to the static seed instead of stopping on an empty success.
        if not response:
            raise NotFoundError(f"No api_football squad for team={team!r}")
        for player in response[0].get("players", []):
            squad.append(
                {
                    "name": player.get("name"),
                    "number": player.get("number"),
                    "position": player.get("position"),
                    "age": player.get("age"),
                }
            )
        return {"squad": squad}

    async def healthcheck(self) -> bool:
        return _has_key()


class APIFootballScorersAdapter:
    name = "api_football"
    budget = _APIFOOTBALL_BUDGET

    async def fetch(self, league: int = _WC_LEAGUE_ID, season: int = _WC_SEASON, **kwargs) -> dict:
        data = await get_json(
            f"{_APIFOOTBALL_BASE}/players/topscorers",
            params={"league": league, "season": season},
            headers=_headers(),
        )
        scorers = []
        for item in data.get("response", []):
            player = item.get("player", {})
            stats = (item.get("statistics") or [{}])[0]
            scorers.append(
                {
                    "name": player.get("name"),
                    "team": stats.get("team", {}).get("name"),
                    "goals": stats.get("goals", {}).get("total"),
                    "assists": stats.get("goals", {}).get("assists"),
                }
            )
        return {"scorers": scorers}

    async def healthcheck(self) -> bool:
        return _has_key()
