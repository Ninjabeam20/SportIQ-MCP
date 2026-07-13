"""Static seed adapters — bundled WC 2026 draw + Elo ratings.

Always enabled, no credentials. Terminators for the groups, fixtures and squad
chains so there is always a last-resort response. Reads ``wc2026.json`` and
``elo_seed.json`` shipped in ``football/data/``.
"""
from __future__ import annotations

import json
from pathlib import Path

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


def load_football_squads() -> dict:
    return _load("football_squads.json")


class StaticSeedGroupsAdapter:
    """Terminator for the groups chain — the canonical 2026 draw + Elo ratings."""

    name = "static_seed"
    health_name = "football_static_seed"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        wc = load_wc2026()
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


class StaticSeedSquadAdapter:
    """Squad terminator. Bundles marquee WC rosters in ``football_squads.json``;
    teams without a seeded roster return an empty-but-valid squad with team
    metadata rather than failing (preserves the NOT_FOUND terminator invariant)."""

    name = "static_seed"
    health_name = "football_static_seed"
    budget = None

    async def fetch(self, team: str, **kwargs) -> dict:
        wc = load_wc2026()
        code = team.upper()
        meta = wc.get("teams", {}).get(code, {})
        squads = load_football_squads()
        return {
            "squad": squads.get(code, []),
            "team": code,
            "team_name": meta.get("name", team),
            "source": "static_seed",
        }

    async def healthcheck(self) -> bool:
        return (_DATA_DIR / "wc2026.json").exists()
