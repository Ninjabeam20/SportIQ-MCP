"""CricSheet adapter tests — HTTP mocked with respx."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.cricket.adapters.cricsheet import CricSheetPlayerStatsAdapter, CricSheetSquadAdapter

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "cricsheet"


def _load(name: str) -> list:
    return json.loads((_FIXTURES / name).read_text())


@respx.mock
async def test_player_stats_adapter_returns_all_players():
    fixture = _load("player_stats_sample.json")
    respx.get("https://cricsheet.org/register/people.json").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricSheetPlayerStatsAdapter()
    result = await adapter.fetch()
    assert "players" in result
    assert len(result["players"]) == 2


@respx.mock
async def test_player_stats_adapter_filters_by_name():
    fixture = _load("player_stats_sample.json")
    respx.get("https://cricsheet.org/register/people.json").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricSheetPlayerStatsAdapter()
    result = await adapter.fetch(player_name="Kohli")
    assert len(result["players"]) == 1
    assert "Kohli" in result["players"][0]["name"]


@respx.mock
async def test_squad_adapter_filters_by_team():
    fixture = _load("squad_sample.json")
    respx.get("https://cricsheet.org/register/people.json").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricSheetSquadAdapter()
    result = await adapter.fetch(team="Mumbai Indians")
    assert "players" in result
    assert all("Mumbai Indians" in p["teams"] for p in result["players"])


@respx.mock
async def test_cricsheet_healthcheck_true_when_reachable():
    fixture = _load("player_stats_sample.json")
    respx.get("https://cricsheet.org/register/people.json").mock(
        return_value=Response(200, json=fixture)
    )
    adapter = CricSheetPlayerStatsAdapter()
    assert await adapter.healthcheck() is True
