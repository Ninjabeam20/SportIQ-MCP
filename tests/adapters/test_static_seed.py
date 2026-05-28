"""Static seed adapter tests — no HTTP, reads local JSON."""

import pytest

from sportiq.core.errors import NotFoundError
from sportiq.cricket.adapters.static_seed import (
    StaticSeedSquadAdapter,
    StaticSeedVenueAdapter,
)


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


async def test_venue_adapter_returns_record_for_known_venue():
    adapter = StaticSeedVenueAdapter()
    result = await adapter.fetch(venue="Wankhede")
    assert result["city"] == "Mumbai"
    assert result["pitch_type"] == "batting"
    assert result["source"] == "static_seed"


async def test_venue_adapter_matches_city_name():
    adapter = StaticSeedVenueAdapter()
    result = await adapter.fetch(venue="Chennai")
    assert "Chidambaram" in result["name"]


async def test_venue_adapter_raises_for_unknown_venue():
    adapter = StaticSeedVenueAdapter()
    with pytest.raises(NotFoundError):
        await adapter.fetch(venue="unknown-stadium")


async def test_venue_adapter_healthcheck_true_when_json_exists():
    adapter = StaticSeedVenueAdapter()
    assert await adapter.healthcheck() is True
