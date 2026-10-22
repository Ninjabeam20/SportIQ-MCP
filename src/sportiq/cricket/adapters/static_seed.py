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


def _load_squads() -> dict:
    """The bundled squad seed without its ``_meta`` provenance block."""
    return {k: v for k, v in (_load("squads.json") or {}).items() if not k.startswith("_")}


def seed_team_codes() -> list[str]:
    """Team codes present in the bundled squad seed (e.g. ``MI``, ``CSK``)."""
    return list(_load_squads())


class StaticSeedSquadAdapter:
    name = "static_seed"
    health_name = "cricket_static_seed"
    budget = None  # local JSON read, no upstream to rate-limit

    async def fetch(self, team: str | None = None, series_id: str | None = None, **kwargs) -> dict:
        from sportiq.cricket.adapters._normalize import normalise_squad_payload
        from sportiq.cricket.teams import resolve_team_code

        squads = _load_squads()
        if team:
            # Accept a code ("MI") or an official name ("Mumbai Indians").
            team_upper = resolve_team_code(team, squads.keys()) or team.upper()
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
        # Lookup is case-insensitive and tolerates the city or short slug, plus
        # provider strings like "Wankhede Stadium, Mumbai".
        wanted = venue.strip().lower()
        head, _, tail = (part.strip() for part in wanted.partition(","))

        def _candidates(key: str, record: dict) -> set[str]:
            return {
                key.lower(),
                (record.get("name") or "").lower(),
                (record.get("city") or "").lower(),
            }

        def _name_prefix(record: dict) -> bool:
            name = (record.get("name") or "").lower()
            if len(head) < 5 or len(name) < 5:
                return False
            return name.startswith(head) or head.startswith(name)

        matchers = (
            lambda key, record: wanted in _candidates(key, record),
            lambda key, record: head in _candidates(key, record),
            lambda key, record: _name_prefix(record),
            lambda key, record: bool(tail) and tail == (record.get("city") or "").lower(),
        )
        for matches in matchers:
            for key, record in venues.items():
                if matches(key, record):
                    return {**record, "key": key, "source": "static_seed"}
        known = ", ".join(sorted(venues))
        raise NotFoundError(f"No venue matching {venue!r} in static seed. Known venues: {known}")

    async def healthcheck(self) -> bool:
        return (_DATA_DIR / "venues.json").exists()
