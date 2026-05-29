"""The Odds API adapter — live bookmaker odds for IPL cricket.

Free tier: 500 req/month, shared across sports (one `theodds` budget). Requires
THEODDS_KEY; raises MissingCredentialsError when absent so the chain walks past.

The Odds API has no concept of CricAPI match_ids — it returns a rolling list of
upcoming events, each with its own opaque event id, the two team names and
per-bookmaker h2h prices. This adapter fetches the whole IPL list and normalises
it; the tool layer applies any team-name filter (so the cache key stays
sport-wide). Mapping a CricAPI match_id to an Odds-API event is a deferred
follow-up (same posture as the football squad id resolution).

The normaliser is intentionally duplicated in the football adapter rather than
shared — two short self-contained files (one per sport-specific endpoint) over a
cross-package helper. The shared piece is the HTTP client (core.http).
"""
from __future__ import annotations

from sportiq.config import settings
from sportiq.core.errors import MissingCredentialsError
from sportiq.core.http import get_json
from sportiq.core.ratelimit import Budget

_THEODDS_BASE = "https://api.the-odds-api.com/v4"

# 500 req/month free tier ≈ 16/day; the Budget primitive has no per-month unit,
# so we gate at a daily slice shared across cricket + football (one `theodds`
# source). When the slice is spent the chain serves stale odds (24h ceiling).
_THEODDS_BUDGET = Budget(source="theodds", per_day=16)

_SPORT_KEY = "cricket_ipl"
_REGIONS = "uk,eu"  # better IPL + international bookmaker coverage than us


def _key() -> str:
    if not settings.theodds_key:
        raise MissingCredentialsError("THEODDS_KEY is not set")
    return settings.theodds_key


def _normalise_events(events: list[dict]) -> list[dict]:
    """Flatten The Odds API events into {event_id, home, away, commence_time, bookmakers}.

    Each bookmaker is reduced to its h2h home/away decimal price.
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
                {"name": bk.get("title"), "home": prices.get(home), "away": prices.get(away)}
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


class TheOddsCricketAdapter:
    name = "theodds"
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
