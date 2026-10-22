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


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _standings_list(data: object) -> dict:
    if not isinstance(data, dict):
        return {}
    lists = data.get("MRData", {}).get("StandingsTable", {}).get("StandingsLists", [])
    return lists[0] if lists and isinstance(lists, list) else {}


def _normalize_standings(year: int, driver_res: object, constructor_res: object) -> dict:
    """Map Jolpica MRData into the shared F1 standings shape (see FastF1 adapter)."""
    d_list = _standings_list(driver_res)
    c_list = _standings_list(constructor_res)
    drivers = []
    for row in d_list.get("DriverStandings", []):
        drv = row.get("Driver", {})
        teams = row.get("Constructors") or [{}]
        name = " ".join(p for p in (drv.get("givenName"), drv.get("familyName")) if p)
        drivers.append(
            {
                "position": _int_or_none(row.get("position")) or 0,
                "driver_number": _int_or_none(drv.get("permanentNumber")),
                "code": drv.get("code") or (drv.get("familyName") or "")[:3].upper(),
                "name": name,
                "team": teams[-1].get("name", ""),
                "points": float(row.get("points") or 0),
                "wins": _int_or_none(row.get("wins")) or 0,
            }
        )
    constructors = [
        {
            "position": _int_or_none(row.get("position")) or 0,
            "team": row.get("Constructor", {}).get("name", ""),
            "points": float(row.get("points") or 0),
            "wins": _int_or_none(row.get("wins")) or 0,
        }
        for row in c_list.get("ConstructorStandings", [])
    ]
    return {
        "season": _int_or_none(d_list.get("season") or c_list.get("season")) or year,
        "round": _int_or_none(d_list.get("round") or c_list.get("round")) or 0,
        "drivers": drivers,
        "constructors": constructors,
    }


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

        return _normalize_standings(
            year,
            driver_res if has_driver else {},
            constructor_res if has_constructor else {},
        )

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
