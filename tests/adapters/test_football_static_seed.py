"""Football static-seed squad terminator — marquee rosters + empty-but-valid fallback."""
from __future__ import annotations

from sportiq.football.adapters.static_seed import StaticSeedSquadAdapter


async def test_squad_terminator_returns_marquee_roster():
    """A seeded marquee team (ARG) returns real players from football_squads.json."""
    result = await StaticSeedSquadAdapter().fetch(team="ARG")
    assert result["source"] == "static_seed"
    assert result["team"] == "ARG"
    assert len(result["squad"]) > 0
    assert any(p["name"] == "Lionel Messi" for p in result["squad"])
    assert all("position" in p for p in result["squad"])


async def test_squad_terminator_unknown_team_empty_but_valid():
    """An unseeded team returns an empty-but-valid squad — no raise (preserves the
    NOT_FOUND terminator invariant)."""
    result = await StaticSeedSquadAdapter().fetch(team="ZZZ")
    assert result["source"] == "static_seed"
    assert result["team"] == "ZZZ"
    assert result["squad"] == []
