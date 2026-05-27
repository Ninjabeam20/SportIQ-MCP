"""CricAPI adapter — primary free source for live scores, fixtures, standings, squad.

100 req/day free tier. Requires CRICAPI_KEY. Raises MissingCredentialsError when key
is absent so the chain walks past this adapter silently.
"""

from __future__ import annotations

from sportiq.config import settings
from sportiq.core.errors import MissingCredentialsError
from sportiq.core.http import get_json
from sportiq.core.logging import get_logger
from sportiq.core.ratelimit import Budget

log = get_logger(__name__)

_BASE = "https://api.cricapi.com/v1"

# Shared per-source budget. CricAPI's free tier is 100 req/day across every
# endpoint, so all CricAPI adapters share one counter via the `source` key.
_CRICAPI_BUDGET = Budget(source="cricapi", per_day=100)


def _key() -> str:
    if not settings.cricapi_key:
        raise MissingCredentialsError("CRICAPI_KEY is not set")
    return settings.cricapi_key


class CricAPILiveMatchesAdapter:
    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, **kwargs) -> dict:
        k = _key()
        data = await get_json(f"{_BASE}/currentMatches", params={"apikey": k, "offset": 0})
        return {"matches": data.get("data", [])}

    async def healthcheck(self) -> bool:
        if not settings.cricapi_key:
            return False
        try:
            data = await get_json(f"{_BASE}/currentMatches", params={"apikey": settings.cricapi_key, "offset": 0})
            return data.get("status") == "success"
        except Exception:
            return False


class CricAPIScorecardAdapter:
    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, match_id: str, **kwargs) -> dict:
        k = _key()
        return await get_json(f"{_BASE}/match_scorecard", params={"apikey": k, "id": match_id})

    async def healthcheck(self) -> bool:
        return bool(settings.cricapi_key)


class CricAPIPointsTableAdapter:
    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, series_id: str, **kwargs) -> dict:
        k = _key()
        return await get_json(f"{_BASE}/series_points_table", params={"apikey": k, "id": series_id})

    async def healthcheck(self) -> bool:
        return bool(settings.cricapi_key)


class CricAPIScheduleAdapter:
    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, series_id: str | None = None, **kwargs) -> dict:
        k = _key()
        params: dict = {"apikey": k, "offset": 0}
        if series_id:
            params["id"] = series_id
        data = await get_json(f"{_BASE}/matches", params=params)
        return {"matches": data.get("data", [])}

    async def healthcheck(self) -> bool:
        return bool(settings.cricapi_key)


class CricAPISquadAdapter:
    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, series_id: str, **kwargs) -> dict:
        k = _key()
        return await get_json(f"{_BASE}/series_squad", params={"apikey": k, "id": series_id})

    async def healthcheck(self) -> bool:
        return bool(settings.cricapi_key)
