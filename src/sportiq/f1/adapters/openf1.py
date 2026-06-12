"""OpenF1 adapters — live telemetry and session data."""

from __future__ import annotations

from sportiq.core.http import get_json_burst
from sportiq.f1.adapters.base import _OPENF1_BASE


class OpenF1SessionsAdapter:
    name = "openf1"
    budget = None

    async def fetch(
        self,
        year: int | None = None,
        country: str | None = None,
        session_key: int | None = None,
        **kwargs,
    ) -> dict:
        # session_key resolves a single session (carries circuit_key for circuit
        # profiles); year[+country] lists a calendar. Both hit the same endpoint.
        if session_key is None and year is None:
            # A selector-less /sessions query would pull OpenF1's entire history.
            raise ValueError("OpenF1SessionsAdapter.fetch needs year or session_key")
        params: dict = {}
        if session_key is not None:
            params["session_key"] = session_key
        if year is not None:
            params["year"] = year
        if country:
            params["country_name"] = country
        data = await get_json_burst(f"{_OPENF1_BASE}/sessions", params=params)
        return {"sessions": data if isinstance(data, list) else [data]}

    async def healthcheck(self) -> bool:
        return True


class OpenF1DriversAdapter:
    name = "openf1"
    budget = None

    async def fetch(self, session_key: int, **kwargs) -> dict:
        data = await get_json_burst(f"{_OPENF1_BASE}/drivers", params={"session_key": session_key})
        return {"drivers": data if isinstance(data, list) else [data]}

    async def healthcheck(self) -> bool:
        return True


class OpenF1LapsAdapter:
    name = "openf1"
    budget = None

    async def fetch(self, session_key: int, driver_number: int, **kwargs) -> dict:
        data = await get_json_burst(
            f"{_OPENF1_BASE}/laps",
            params={"session_key": session_key, "driver_number": driver_number},
        )
        return {"laps": data if isinstance(data, list) else [data]}

    async def healthcheck(self) -> bool:
        return True


class OpenF1StintsAdapter:
    name = "openf1"
    budget = None

    async def fetch(self, session_key: int, driver_number: int, **kwargs) -> dict:
        data = await get_json_burst(
            f"{_OPENF1_BASE}/stints",
            params={"session_key": session_key, "driver_number": driver_number},
        )
        return {"stints": data if isinstance(data, list) else [data]}

    async def healthcheck(self) -> bool:
        return True


class OpenF1WeatherAdapter:
    name = "openf1"
    budget = None

    async def fetch(self, session_key: int, **kwargs) -> dict:
        data = await get_json_burst(f"{_OPENF1_BASE}/weather", params={"session_key": session_key})
        return {"weather": data if isinstance(data, list) else [data]}

    async def healthcheck(self) -> bool:
        return True
