"""Jolpica (Ergast successor) adapters — season standings and race results."""

from __future__ import annotations

import asyncio

from sportiq.core.errors import NotFoundError
from sportiq.core.http import get_json
from sportiq.f1.adapters.base import _JOLPICA_BASE


def _has_driver_standings(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    lists = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
    if not lists or not isinstance(lists, list):
        return False
    return bool(lists[0].get("DriverStandings"))


def _has_constructor_standings(data: object) -> bool:
    if not isinstance(data, dict):
        return False
    lists = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
    if not lists or not isinstance(lists, list):
        return False
    return bool(lists[0].get("ConstructorStandings"))


class JolpicaStandingsAdapter:
    name = "jolpica"
    budget = None

    async def fetch(self, year: int, **kwargs) -> dict:
        driver_res, constructor_res = await asyncio.gather(
            get_json(f"{_JOLPICA_BASE}/f1/{year}/driverStandings.json"),
            get_json(f"{_JOLPICA_BASE}/f1/{year}/constructorStandings.json"),
            return_exceptions=True,
        )
        has_driver = _has_driver_standings(driver_res)
        has_constructor = _has_constructor_standings(constructor_res)

        if not has_driver and not has_constructor:
            raise NotFoundError(f"Jolpica returned no standings for year {year}")

        return {
            "driver_standings": driver_res if has_driver else {},
            "constructor_standings": constructor_res if has_constructor else {},
        }

    async def healthcheck(self) -> bool:
        return True


class JolpicaResultsAdapter:
    name = "jolpica"
    budget = None

    async def fetch(self, year: int, round: int, **kwargs) -> dict:
        data = await get_json(f"{_JOLPICA_BASE}/f1/{year}/{round}/results.json")
        if not isinstance(data, dict):
            raise NotFoundError(f"Jolpica returned no race results for {year} round {round}")
        races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
        if not races or not races[0].get("Results"):
            raise NotFoundError(f"Jolpica returned no race results for {year} round {round}")
        return {"results": data}

    async def healthcheck(self) -> bool:
        return True
