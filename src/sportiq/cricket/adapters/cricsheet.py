"""CricSheet adapter — free, public-domain, always-enabled historical data.

Downloads from cricsheet.org JSON feeds (no key required). Useful for squad
rosters and player career stats. Not useful for live scores (hours-stale).
"""

from __future__ import annotations

from sportiq.core.http import get_json
from sportiq.core.logging import get_logger

log = get_logger(__name__)

_BASE = "https://cricsheet.org"

# Known people.json endpoint — lightweight, always available
_PEOPLE_URL = f"{_BASE}/register/people.json"


class CricSheetPlayerStatsAdapter:
    name = "cricsheet"

    async def fetch(self, player_name: str | None = None, **kwargs) -> dict:
        data = await get_json(_PEOPLE_URL)

        if player_name:
            name_lower = player_name.lower()
            records = [
                p for p in data
                if name_lower in p.get("name", "").lower()
                or name_lower in p.get("unique_name", "").lower()
            ]
        else:
            records = data[:50]

        return {"players": records}

    async def healthcheck(self) -> bool:
        try:
            data = await get_json(_PEOPLE_URL)
            return isinstance(data, list) and len(data) > 0
        except Exception:
            return False


class CricSheetSquadAdapter:
    name = "cricsheet"

    async def fetch(self, team: str | None = None, **kwargs) -> dict:
        data = await get_json(_PEOPLE_URL)

        if team:
            team_lower = team.lower()
            records = [
                p for p in data
                if any(
                    team_lower in str(t).lower()
                    for t in p.get("teams", [])
                )
            ]
        else:
            records = data[:50]

        return {"players": records, "team": team}

    async def healthcheck(self) -> bool:
        try:
            data = await get_json(_PEOPLE_URL)
            return isinstance(data, list)
        except Exception:
            return False
