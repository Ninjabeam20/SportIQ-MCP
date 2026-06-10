"""RapidAPI Cricbuzz adapter — paid licensed mirror, opt-in via RAPIDAPI_KEY.

Raises MissingCredentialsError when RAPIDAPI_KEY is unset so the chain skips it.
"""

from __future__ import annotations

from urllib.parse import quote

from sportiq.config import settings
from sportiq.core.errors import MissingCredentialsError
from sportiq.core.http import get_json
from sportiq.core.logging import get_logger

log = get_logger(__name__)

_HOST = "cricbuzz-cricket.p.rapidapi.com"
_BASE = f"https://{_HOST}"


def _path_id(value: str) -> str:
    """Percent-encode a user-supplied id used as a URL path segment, so `../`
    or `/` sequences can't redirect the request to another endpoint."""
    return quote(value, safe="")


def _headers() -> dict:
    if not settings.rapidapi_key:
        raise MissingCredentialsError("RAPIDAPI_KEY is not set")
    return {
        "X-RapidAPI-Key": settings.rapidapi_key,
        "X-RapidAPI-Host": _HOST,
    }


class RapidAPICricbuzzLiveAdapter:
    name = "rapidapi_cricbuzz"
    budget = None  # free-tier limits vary by plan; not centrally tracked

    async def fetch(self, **kwargs) -> dict:
        h = _headers()
        data = await get_json(f"{_BASE}/matches/v1/live", headers=h)
        matches = []
        for type_obj in data.get("typeMatches", []):
            for series in type_obj.get("seriesMatches", []):
                for m in series.get("seriesAdWrapper", {}).get("matches", []):
                    matches.append(m.get("matchInfo", {}))
        return {"matches": matches}

    async def healthcheck(self) -> bool:
        return bool(settings.rapidapi_key)


class RapidAPICricbuzzScorecardAdapter:
    name = "rapidapi_cricbuzz"
    budget = None

    async def fetch(self, match_id: str, **kwargs) -> dict:
        h = _headers()
        return await get_json(f"{_BASE}/mcenter/v1/{_path_id(match_id)}/scard", headers=h)

    async def healthcheck(self) -> bool:
        return bool(settings.rapidapi_key)


class RapidAPICricbuzzScheduleAdapter:
    name = "rapidapi_cricbuzz"
    budget = None

    async def fetch(self, series_id: str | None = None, **kwargs) -> dict:
        h = _headers()
        url = f"{_BASE}/matches/v1/upcoming"
        data = await get_json(url, headers=h)
        matches = []
        for type_obj in data.get("typeMatches", []):
            for series in type_obj.get("seriesMatches", []):
                for m in series.get("seriesAdWrapper", {}).get("matches", []):
                    matches.append(m.get("matchInfo", {}))
        return {"matches": matches}

    async def healthcheck(self) -> bool:
        return bool(settings.rapidapi_key)


class RapidAPICricbuzzStandingsAdapter:
    name = "rapidapi_cricbuzz"
    budget = None

    async def fetch(self, series_id: str, **kwargs) -> dict:
        h = _headers()
        data = await get_json(f"{_BASE}/series/v1/{_path_id(series_id)}/points-table", headers=h)
        return data

    async def healthcheck(self) -> bool:
        return bool(settings.rapidapi_key)


class RapidAPICricbuzzPlayerStatsAdapter:
    """`/stats/v1/player/{id}/career` — per-format career stats from Cricbuzz."""

    name = "rapidapi_cricbuzz"
    budget = None

    async def fetch(self, player_id: str, **kwargs) -> dict:
        h = _headers()
        return await get_json(
            f"{_BASE}/stats/v1/player/{_path_id(player_id)}/career", headers=h
        )

    async def healthcheck(self) -> bool:
        return bool(settings.rapidapi_key)
