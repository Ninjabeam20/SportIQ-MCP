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
    assert result["season"] == 2025
    assert isinstance(result["round"], int)
    driver = result["drivers"][0]
    assert set(driver) == {"position", "driver_number", "code", "name", "team", "points", "wins"}
    assert driver["position"] == 1
    assert driver["name"] == "Max Verstappen"
    assert driver["code"] == "VER"
    assert driver["points"] == 136.0
    assert isinstance(driver["points"], float)
    assert isinstance(driver["wins"], int)
    assert driver["driver_number"] is None or isinstance(driver["driver_number"], int)
    assert isinstance(driver["team"], str)
    team = result["constructors"][0]
    assert set(team) == {"position", "team", "points", "wins"}
    assert team == {"position": 1, "team": "Red Bull", "points": 210.0, "wins": 0}


@respx.mock
async def test_jolpica_standings_adapter_maps_full_ergast_row():
    from sportiq.f1.adapters.jolpica import JolpicaStandingsAdapter

    # Field names as Jolpica serves them (the committed fixture is trimmed).
    payload = {
        "MRData": {
            "StandingsTable": {
                "StandingsLists": [
                    {
                        "season": "2026",
                        "round": "17",
                        "DriverStandings": [
                            {
                                "position": "1",
                                "points": "325",
                                "wins": "7",
                                "Driver": {
                                    "permanentNumber": "12",
                                    "code": "ANT",
                                    "givenName": "Andrea Kimi",
                                    "familyName": "Antonelli",
                                },
                                "Constructors": [{"name": "Mercedes"}],
                            }
                        ],
                    }
                ]
            }
        }
    }
    respx.get("https://api.jolpi.ca/ergast/f1/2026/driverStandings.json").mock(
        return_value=Response(200, json=payload)
    )
    respx.get("https://api.jolpi.ca/ergast/f1/2026/constructorStandings.json").mock(
        return_value=Response(500, json={})
    )
    result = await JolpicaStandingsAdapter().fetch(year=2026)
    assert result["round"] == 17
    assert result["drivers"][0] == {
        "position": 1,
        "driver_number": 12,
        "code": "ANT",
        "name": "Andrea Kimi Antonelli",
        "team": "Mercedes",
        "points": 325.0,
        "wins": 7,
    }
    assert result["constructors"] == []


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
    assert result["drivers"][0]["name"] == "Max Verstappen"
    assert result["constructors"] == []


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
    assert result["drivers"] == []
    assert result["constructors"][0]["team"] == "Red Bull"


@respx.mock
async def test_jolpica_schedule_adapter_maps_rounds_dates_and_sprints():
    # schedule_2026.json: one keyless GET of /ergast/f1/2026.json on 2026-10-22, saved unmodified.
    from sportiq.f1.adapters.jolpica import JolpicaScheduleAdapter

    respx.get("https://api.jolpi.ca/ergast/f1/2026.json").mock(
        return_value=Response(200, json=_load("schedule_2026.json"))
    )
    result = await JolpicaScheduleAdapter().fetch(year=2026)
    races = result["races"]
    assert result["season"] == 2026
    assert len(races) == 23
    assert set(races[0]) == {"round", "raceName", "date", "sprint"}
    singapore = next(r for r in races if r["round"] == 17)
    assert singapore["sprint"] is True
    assert races[-1] == {
        "round": 23,
        "raceName": "Abu Dhabi Grand Prix",
        "date": "2026-12-06",
        "sprint": False,
    }


@respx.mock
async def test_jolpica_schedule_adapter_empty_raises_not_found():
    from sportiq.f1.adapters.jolpica import JolpicaScheduleAdapter

    respx.get("https://api.jolpi.ca/ergast/f1/2031.json").mock(
        return_value=Response(200, json={"MRData": {"RaceTable": {"Races": []}}})
    )
    with pytest.raises(NotFoundError):
        await JolpicaScheduleAdapter().fetch(year=2031)
