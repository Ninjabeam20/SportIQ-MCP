"""CricAPI adapter — primary free source for live scores, fixtures, standings, squad.

100 req/day free tier. Requires CRICAPI_KEY. Raises MissingCredentialsError when key
is absent so the chain walks past this adapter silently.
"""

from __future__ import annotations

from sportiq.config import settings
from sportiq.core.errors import MissingCredentialsError, NotFoundError
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


def _unwrap(resp: dict) -> dict:
    """Return CricAPI's inner ``data``, raising on a non-success envelope.

    CricAPI wraps every response as ``{apikey, status, data?, reason?}``. On
    failure (``status != "success"``) it omits ``data`` and echoes the request
    ``apikey`` — so returning the raw response both leaks the key and lets a
    "not found" / error response masquerade as a successful empty result. This
    strips the envelope (apikey never reaches tool output) and raises
    ``NotFoundError`` on failure so the chain falls through to the next adapter.
    """
    if resp.get("status") != "success":
        raise NotFoundError(resp.get("reason") or "CricAPI request failed")
    return resp.get("data", {})


class CricAPILiveMatchesAdapter:
    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, **kwargs) -> dict:
        k = _key()
        raw = await get_json(f"{_BASE}/currentMatches", params={"apikey": k, "offset": 0})
        return {"matches": _unwrap(raw) or []}

    async def healthcheck(self) -> bool:
        # Key-presence only — a live call here would burn a CricAPI quota token
        # on every sportiq_health() invocation (publicly callable on the hosted
        # endpoint) without going through the chain's budget gate.
        return bool(settings.cricapi_key)


class CricAPIScorecardAdapter:
    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, match_id: str, **kwargs) -> dict:
        k = _key()
        raw = await get_json(f"{_BASE}/match_scorecard", params={"apikey": k, "id": match_id})
        return _unwrap(raw)

    async def healthcheck(self) -> bool:
        return bool(settings.cricapi_key)


class CricAPIPointsTableAdapter:
    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, series_id: str, **kwargs) -> dict:
        k = _key()
        raw = await get_json(f"{_BASE}/series_points_table", params={"apikey": k, "id": series_id})
        return _unwrap(raw)

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
        raw = await get_json(f"{_BASE}/matches", params=params)
        return {"matches": _unwrap(raw) or []}

    async def healthcheck(self) -> bool:
        return bool(settings.cricapi_key)


class CricAPIPlayerInfoAdapter:
    """`/v1/players_info?id=<player_id>` — player profile + career stats by id."""

    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, player_id: str, **kwargs) -> dict:
        k = _key()
        raw = await get_json(
            f"{_BASE}/players_info", params={"apikey": k, "id": player_id}
        )
        return _unwrap(raw)

    async def healthcheck(self) -> bool:
        return bool(settings.cricapi_key)


# Reserved for cricket_search_player (Phase 3+); not yet chain-wired.
class CricAPIPlayerSearchAdapter:
    """`/v1/players?search=<name>` — directory search by player name."""

    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, name: str, **kwargs) -> dict:
        k = _key()
        return await get_json(
            f"{_BASE}/players", params={"apikey": k, "offset": 0, "search": name}
        )

    async def healthcheck(self) -> bool:
        return bool(settings.cricapi_key)


class CricAPISquadAdapter:
    name = "cricapi"
    budget = _CRICAPI_BUDGET

    async def fetch(self, series_id: str | None = None, team: str | None = None, **kwargs) -> dict:
        from sportiq.cricket.adapters._normalize import normalise_squad_payload

        # CricAPI squad is series-scoped. Without a series_id there's nothing to
        # query — raise so the chain falls through to the static_seed terminator
        # (which serves the team roster offline) rather than burning a call and
        # caching an empty result that shadows the seed.
        if not series_id:
            raise NotFoundError("CricAPI squad requires a series_id")

        k = _key()
        raw = await get_json(
            f"{_BASE}/series_squad", params={"apikey": k, "id": series_id}
        )
        if raw.get("status") != "success":
            raise NotFoundError(raw.get("reason") or "CricAPI squad lookup failed")
        return normalise_squad_payload(raw, source="cricapi", team=team)

    async def healthcheck(self) -> bool:
        return bool(settings.cricapi_key)
