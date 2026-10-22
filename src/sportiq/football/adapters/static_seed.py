"""Static seed adapters — bundled WC 2026 draw + Elo ratings.

Always enabled, no credentials. Terminators for the groups, fixtures and squad
chains so there is always a last-resort response. Reads ``wc2026.json`` and
``elo_seed.json`` shipped in ``football/data/``.
"""

from __future__ import annotations

import json
from pathlib import Path

from sportiq.core.errors import NotFoundError

_DATA_DIR = Path(__file__).parent.parent / "data"


def _load(filename: str) -> dict:
    path = _DATA_DIR / filename
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def load_wc2026() -> dict:
    return _load("wc2026.json")


def load_elo_seed() -> dict:
    return _load("elo_seed.json")


class StaticSeedGroupsAdapter:
    """Terminator for the groups chain — the canonical 2026 draw + Elo ratings."""

    name = "static_seed"
    health_name = "football_static_seed"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        wc = load_wc2026()
        if not wc.get("groups") or not load_elo_seed():
            raise NotFoundError("static_seed groups/ratings unavailable (missing data file)")
        return {
            "groups": wc.get("groups", {}),
            "format": wc.get("format", {}),
            "teams": wc.get("teams", {}),
            "ratings": load_elo_seed(),
            "source": "static_seed",
        }

    async def healthcheck(self) -> bool:
        return (_DATA_DIR / "wc2026.json").exists()


class StaticSeedFixturesAdapter:
    """Fixtures terminator — synthesises the group-stage round-robin from the draw."""

    name = "static_seed"
    health_name = "football_static_seed"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        wc = load_wc2026()
        if not wc.get("groups"):
            raise NotFoundError("static_seed fixtures unavailable (missing data file)")
        teams_meta = wc.get("teams", {})
        fixtures = []
        for group, teams in wc.get("groups", {}).items():
            for i in range(len(teams)):
                for j in range(i + 1, len(teams)):
                    home, away = teams[i], teams[j]
                    pair_id = ":".join(sorted((home, away)))
                    fixtures.append(
                        {
                            "match_id": f"static:group:{group}:{pair_id}",
                            "home": teams_meta.get(home, {}).get("name", home),
                            "away": teams_meta.get(away, {}).get("name", away),
                            "group": group,
                            "stage": "GROUP",
                            "status": "SCHEDULED",
                            "home_goals": None,
                            "away_goals": None,
                            "winner": None,
                        }
                    )
        return {"fixtures": fixtures, "source": "static_seed"}

    async def healthcheck(self) -> bool:
        return (_DATA_DIR / "wc2026.json").exists()


# No bundled rosters (opus D6: the hand-written seed was removed — no
# hand-curated player data). The terminator stays empty-but-valid.
SQUAD_NOTE = "No bundled squads; set APIFOOTBALL_KEY for live squads."


class StaticSeedSquadAdapter:
    """Squad terminator. Ships no rosters: every team returns an empty-but-valid
    squad with team metadata and a ``note`` rather than failing (preserves the
    NOT_FOUND terminator invariant)."""

    name = "static_seed"
    health_name = "football_static_seed"
    budget = None

    async def fetch(self, team: str, **kwargs) -> dict:
        wc = load_wc2026()
        code = team.upper()
        meta = wc.get("teams", {}).get(code, {})
        return {
            "squad": [],
            "team": code,
            "team_name": meta.get("name", team),
            "source": "static_seed",
            "note": SQUAD_NOTE,
        }

    async def healthcheck(self) -> bool:
        return (_DATA_DIR / "wc2026.json").exists()
