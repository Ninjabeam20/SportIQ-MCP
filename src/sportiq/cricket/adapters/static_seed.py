"""Static seed adapter — reads local JSON bundles shipped with the package.

Always enabled, no credentials. Used as the terminator for the squad and
pitch-data chains so there is always a last-resort response even when all
network adapters fail. One adapter class per data file.
"""

from __future__ import annotations

import json
from pathlib import Path

from sportiq.core.errors import NotFoundError
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
    health_name = "cricket_static_seed"
    budget = None  # local JSON read, no upstream to rate-limit

    async def fetch(self, team: str | None = None, series_id: str | None = None, **kwargs) -> dict:
        from sportiq.cricket.adapters._normalize import normalise_squad_payload

        squads = _load("squads.json")
        if team:
            team_upper = team.upper()
            players = squads.get(team_upper, squads.get(team, []))
            raw = {"players": players}
            return normalise_squad_payload(raw, source="static_seed", team=team_upper)
        return {"squads": squads, "source": "static_seed"}

    async def healthcheck(self) -> bool:
        return (_DATA_DIR / "squads.json").exists()


class StaticSeedVenueAdapter:
    """Looks up venue metadata from the bundled venues.json."""

    name = "static_seed"
    health_name = "cricket_static_seed"
    budget = None

    async def fetch(self, venue: str, **kwargs) -> dict:
        venues = _load("venues.json") or {}
        # Lookup is case-insensitive and tolerates the city or short slug.
        wanted = venue.strip().lower()
        for key, record in venues.items():
            candidates = {
                key.lower(),
                record.get("name", "").lower(),
                record.get("city", "").lower(),
            }
            if wanted in candidates:
                return {**record, "key": key, "source": "static_seed"}
        raise NotFoundError(f"No venue matching {venue!r} in static seed")

    async def healthcheck(self) -> bool:
        return (_DATA_DIR / "venues.json").exists()
