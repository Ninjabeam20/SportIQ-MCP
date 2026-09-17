"""Jolpica adapter tests — all HTTP mocked with respx."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from sportiq.core.errors import NotFoundError

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "jolpica"


def _load(name: str) -> dict:
    return json.loads((_FIXTURES / name).read_text())


@respx.mock
async def test_jolpica_standings_adapter_returns_driver_and_constructor_blocks():
    from sportiq.f1.adapters.jolpica import JolpicaStandingsAdapter

    respx.get("https://api.jolpi.ca/ergast/f1/2025/driverStandings.json").mock(
        return_value=Response(200, json=_load("standings_2025.json"))
    )
    respx.get("https://api.jolpi.ca/ergast/f1/2025/constructorStandings.json").mock(
        return_value=Response(200, json=_load("constructor_standings_2025.json"))
    )
    result = await JolpicaStandingsAdapter().fetch(year=2025)
    assert "driver_standings" in result
    assert "constructor_standings" in result
    driver_list = result["driver_standings"]["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
    assert driver_list[0]["Driver"]["driverId"] == "verstappen"
    constructor_list = result["constructor_standings"]["MRData"]["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]
    assert constructor_list[0]["Constructor"]["constructorId"] == "red_bull"


@respx.mock
async def test_jolpica_results_adapter_returns_race_results():
    from sportiq.f1.adapters.jolpica import JolpicaResultsAdapter

    respx.get("https://api.jolpi.ca/ergast/f1/2025/1/results.json").mock(
        return_value=Response(200, json=_load("results_2025_round1.json"))
    )
    result = await JolpicaResultsAdapter().fetch(year=2025, round=1)
    assert "results" in result
    races = result["results"]["MRData"]["RaceTable"]["Races"]
    assert races[0]["raceName"] == "Bahrain Grand Prix"
    assert races[0]["Results"][0]["Driver"]["driverId"] == "verstappen"


@respx.mock
async def test_jolpica_results_adapter_empty_raises_not_found():
    from sportiq.f1.adapters.jolpica import JolpicaResultsAdapter

    respx.get("https://api.jolpi.ca/ergast/f1/2025/1/results.json").mock(
        return_value=Response(200, json={"MRData": {"RaceTable": {"Races": []}}})
    )
    with pytest.raises(NotFoundError, match="no race results"):
        await JolpicaResultsAdapter().fetch(year=2025, round=1)


@respx.mock
async def test_jolpica_standings_adapter_empty_both_raises_not_found():
    from sportiq.f1.adapters.jolpica import JolpicaStandingsAdapter

    empty_payload = {"MRData": {"StandingsTable": {"StandingsLists": []}}}
    respx.get("https://api.jolpi.ca/ergast/f1/2025/driverStandings.json").mock(
        return_value=Response(200, json=empty_payload)
    )
    respx.get("https://api.jolpi.ca/ergast/f1/2025/constructorStandings.json").mock(
        return_value=Response(200, json=empty_payload)
    )
    with pytest.raises(NotFoundError, match="no standings"):
        await JolpicaStandingsAdapter().fetch(year=2025)


@respx.mock
async def test_jolpica_standings_adapter_partial_driver_only():
    from sportiq.f1.adapters.jolpica import JolpicaStandingsAdapter

    respx.get("https://api.jolpi.ca/ergast/f1/2025/driverStandings.json").mock(
        return_value=Response(200, json=_load("standings_2025.json"))
    )
    respx.get("https://api.jolpi.ca/ergast/f1/2025/constructorStandings.json").mock(
        return_value=Response(500, json={})
    )
    result = await JolpicaStandingsAdapter().fetch(year=2025)
    assert "driver_standings" in result
    assert result["constructor_standings"] == {}
    driver_list = result["driver_standings"]["MRData"]["StandingsTable"]["StandingsLists"][0]["DriverStandings"]
    assert driver_list[0]["Driver"]["driverId"] == "verstappen"


@respx.mock
async def test_jolpica_standings_adapter_partial_constructor_only():
    from sportiq.f1.adapters.jolpica import JolpicaStandingsAdapter

    respx.get("https://api.jolpi.ca/ergast/f1/2025/driverStandings.json").mock(
        return_value=Response(200, json={"MRData": {"StandingsTable": {"StandingsLists": []}}})
    )
    respx.get("https://api.jolpi.ca/ergast/f1/2025/constructorStandings.json").mock(
        return_value=Response(200, json=_load("constructor_standings_2025.json"))
    )
    result = await JolpicaStandingsAdapter().fetch(year=2025)
    assert result["driver_standings"] == {}
    assert "constructor_standings" in result
    constructor_list = result["constructor_standings"]["MRData"]["StandingsTable"]["StandingsLists"][0]["ConstructorStandings"]
    assert constructor_list[0]["Constructor"]["constructorId"] == "red_bull"
