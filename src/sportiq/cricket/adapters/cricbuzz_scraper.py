"""Cricbuzz scraper — opt-in fallback.

BeautifulSoup + httpx against m.cricbuzz.com. Must be enabled with
SPORTIQ_ENABLE_CRICBUZZ=1. Raises MissingCredentialsError when disabled.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from sportiq.config import settings
from sportiq.core.errors import MissingCredentialsError
from sportiq.core.http import get_client
from sportiq.core.logging import get_logger

log = get_logger(__name__)

_BASE = "https://m.cricbuzz.com"
_LIVE_URL = f"{_BASE}/cricket-match/live-scores"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 11; SM-G991B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _check_enabled() -> None:
    if not settings.enable_cricbuzz_scraper:
        raise MissingCredentialsError(
            "Cricbuzz scraper is disabled; set SPORTIQ_ENABLE_CRICBUZZ=1"
        )


class CricbuzzLiveMatchesAdapter:
    name = "cricbuzz_scraper"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        _check_enabled()
        client = get_client()
        resp = await client.get(_LIVE_URL, headers=_HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        matches = _parse_live(soup)
        return {"matches": matches}

    async def healthcheck(self) -> bool:
        return settings.enable_cricbuzz_scraper


def _parse_live(soup: BeautifulSoup) -> list[dict]:
    matches = []
    for item in soup.select(".cb-mtch-lst, .cb-lv-scrs-col, [class*='match']")[:10]:
        text = item.get_text(separator=" ", strip=True)
        if text:
            matches.append({"raw": text[:200]})
    return matches
