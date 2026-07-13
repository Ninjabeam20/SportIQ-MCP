"""The Odds API adapter — live bookmaker odds for the FIFA World Cup 2026.

Free tier: 500 req/month, shared across sports (one `theodds` budget, same
counter as the cricket adapter). Requires THEODDS_KEY; raises
MissingCredentialsError when absent so the chain walks past.

Returns a rolling list of upcoming WC events, each with its own event id, the
two team names and per-bookmaker h2h prices. The tool layer applies any
team-name filter (the cache key stays sport-wide). Mirrors the cricket adapter;
the normaliser is duplicated by design rather than shared cross-package.
"""
from __future__ import annotations

from sportiq.config import settings
from sportiq.core.errors import MissingCredentialsError
from sportiq.core.http import get_json
from sportiq.core.ratelimit import Budget

_THEODDS_BASE = "https://api.the-odds-api.com/v4"

# Shared per-source budget with the cricket adapter (one `theodds` source) — the
# 500 req/month free tier covers both sports. ≈16/day; on exhaustion the chain
# serves stale odds within the 24h ceiling.
_THEODDS_BUDGET = Budget(source="theodds", per_day=16)

_SPORT_KEY = "soccer_fifa_world_cup"
# Single region = 1 credit/request (per_day=16 ≈ 480/month, under the 500/month
# free-tier cap). "uk,eu" billed 2 credits/request (~960/month, over cap).
_REGIONS = "uk"


def _key() -> str:
    if not settings.theodds_key:
        raise MissingCredentialsError("THEODDS_KEY is not set")
    return settings.theodds_key


def _normalise_events(events: list[dict]) -> list[dict]:
    """Flatten The Odds API events into {event_id, home, away, commence_time, bookmakers}.

    Soccer h2h is 1X2, so each bookmaker keeps the home/draw/away decimal prices.
    """
    out = []
    for ev in events:
        home, away = ev.get("home_team"), ev.get("away_team")
        bookmakers = []
        for bk in ev.get("bookmakers", []):
            h2h = next((m for m in bk.get("markets", []) if m.get("key") == "h2h"), None)
            if not h2h:
                continue
            prices = {o.get("name"): o.get("price") for o in h2h.get("outcomes", [])}
            bookmakers.append(
                {
                    "name": bk.get("title"),
                    "home": prices.get(home),
                    "draw": prices.get("Draw"),
                    "away": prices.get(away),
                }
            )
        out.append(
            {
                "event_id": ev.get("id"),
                "home": home,
                "away": away,
                "commence_time": ev.get("commence_time"),
                "bookmakers": bookmakers,
            }
        )
    return out


class TheOddsFootballAdapter:
    name = "theodds"
    health_name = "theodds"
    budget = _THEODDS_BUDGET

    async def fetch(self, **kwargs) -> dict:
        data = await get_json(
            f"{_THEODDS_BASE}/sports/{_SPORT_KEY}/odds",
            params={
                "apiKey": _key(),
                "regions": _REGIONS,
                "markets": "h2h",
                "oddsFormat": "decimal",
            },
        )
        return {"events": _normalise_events(data)}

    async def healthcheck(self) -> bool:
        return bool(settings.theodds_key)
