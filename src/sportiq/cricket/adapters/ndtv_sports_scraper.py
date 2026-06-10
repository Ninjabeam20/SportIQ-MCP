"""NDTV Sports cricket scraper — opt-in fallback.

BeautifulSoup + httpx. Must be enabled with SPORTIQ_ENABLE_NDTV=1.
Raises MissingCredentialsError when disabled so the chain skips it.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from sportiq.config import settings
from sportiq.core.errors import MissingCredentialsError
from sportiq.core.http import get_client
from sportiq.core.logging import get_logger
from sportiq.core.ratelimit import Budget

log = get_logger(__name__)

# Courtesy throttle per .claude/rules/api-budgets.md: ≤1 req/3s to avoid an IP
# block. 20/min averages exactly that; the chain's budget gate enforces it.
_NDTV_BUDGET = Budget(source="ndtv_sports_scraper", per_minute=20)

_LIVE_URL = "https://sports.ndtv.com/cricket/live-scores"
_SCHEDULE_URL = "https://sports.ndtv.com/cricket/schedule"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _check_enabled() -> None:
    if not settings.enable_ndtv_scraper:
        raise MissingCredentialsError("NDTV scraper is disabled; set SPORTIQ_ENABLE_NDTV=1")


class NDTVLiveMatchesAdapter:
    name = "ndtv_sports_scraper"
    budget = _NDTV_BUDGET

    async def fetch(self, **kwargs) -> dict:
        _check_enabled()
        client = get_client()
        resp = await client.get(_LIVE_URL, headers=_HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        matches = _parse_live_matches(soup)
        return {"matches": matches}

    async def healthcheck(self) -> bool:
        return settings.enable_ndtv_scraper


class NDTVScheduleAdapter:
    name = "ndtv_sports_scraper"
    budget = _NDTV_BUDGET

    async def fetch(self, series_id: str | None = None, **kwargs) -> dict:
        _check_enabled()
        client = get_client()
        resp = await client.get(_SCHEDULE_URL, headers=_HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        matches = _parse_schedule(soup)
        return {"matches": matches}

    async def healthcheck(self) -> bool:
        return settings.enable_ndtv_scraper


def _parse_live_matches(soup: BeautifulSoup) -> list[dict]:
    matches = []
    for card in soup.select(".match-card, .sp-scr_wrp, [class*='live-score']")[:10]:
        title = card.get_text(separator=" ", strip=True)
        if title:
            matches.append({"raw": title[:200]})
    return matches


def _parse_schedule(soup: BeautifulSoup) -> list[dict]:
    matches = []
    for row in soup.select(".match-card, .schedule-item, [class*='match']")[:20]:
        text = row.get_text(separator=" ", strip=True)
        if text:
            matches.append({"raw": text[:200]})
    return matches
