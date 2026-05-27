"""Static seed adapter — reads local JSON bundles shipped with the package.

Always enabled, no credentials. Used as the terminator for squad chains so
there is always a last-resort response even when all network adapters fail.
venues.json arrives in Phase 2; only squads.json ships in Phase 1.
"""

from __future__ import annotations

import json
from pathlib import Path

from sportiq.core.logging import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"


def _load(filename: str) -> dict | list:
    path = _DATA_DIR / filename
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


class StaticSeedSquadAdapter:
    name = "static_seed"
    budget = None  # local JSON read, no upstream to rate-limit

    async def fetch(self, team: str | None = None, series_id: str | None = None, **kwargs) -> dict:
        squads = _load("squads.json")
        if team:
            team_upper = team.upper()
            players = squads.get(team_upper, squads.get(team, []))
            return {"players": players, "team": team, "source": "static_seed"}
        return {"squads": squads, "source": "static_seed"}

    async def healthcheck(self) -> bool:
        return (_DATA_DIR / "squads.json").exists()
