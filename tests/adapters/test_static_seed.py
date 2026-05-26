"""Static seed adapter tests — no HTTP, reads local JSON."""

from sportiq.cricket.adapters.static_seed import StaticSeedSquadAdapter


async def test_returns_squad_for_known_team():
    adapter = StaticSeedSquadAdapter()
    result = await adapter.fetch(team="MI")
    assert "players" in result
    assert len(result["players"]) > 0
    assert result["team"] == "MI"
    assert result["source"] == "static_seed"


async def test_returns_all_squads_when_no_team():
    adapter = StaticSeedSquadAdapter()
    result = await adapter.fetch()
    assert "squads" in result
    assert "CSK" in result["squads"]
    assert "MI" in result["squads"]


async def test_team_lookup_is_case_insensitive():
    adapter = StaticSeedSquadAdapter()
    upper = await adapter.fetch(team="CSK")
    lower = await adapter.fetch(team="csk")
    assert upper["players"] == lower["players"]


async def test_healthcheck_true_when_json_exists():
    adapter = StaticSeedSquadAdapter()
    assert await adapter.healthcheck() is True
