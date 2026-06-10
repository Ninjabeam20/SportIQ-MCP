"""Jolpica (Ergast successor) adapters — season standings and race results."""

from __future__ import annotations

import asyncio

from sportiq.core.http import get_json
from sportiq.f1.adapters.base import _JOLPICA_BASE


class JolpicaStandingsAdapter:
    name = "jolpica"
    budget = None

    async def fetch(self, year: int, **kwargs) -> dict:
        driver_data, constructor_data = await asyncio.gather(
            get_json(f"{_JOLPICA_BASE}/f1/{year}/driverStandings.json"),
            get_json(f"{_JOLPICA_BASE}/f1/{year}/constructorStandings.json"),
        )
        return {
            "driver_standings": driver_data,
            "constructor_standings": constructor_data,
        }

    async def healthcheck(self) -> bool:
        return True


class JolpicaResultsAdapter:
    name = "jolpica"
    budget = None

    async def fetch(self, year: int, round: int, **kwargs) -> dict:
        data = await get_json(f"{_JOLPICA_BASE}/f1/{year}/{round}/results.json")
        return {"results": data}

    async def healthcheck(self) -> bool:
        return True
