"""OpenF1 adapters — live telemetry and session data."""

from __future__ import annotations

import httpx

from sportiq.core.errors import NotFoundError
from sportiq.core.http import get_json_burst
from sportiq.f1.adapters.base import _OPENF1_BASE


async def _openf1_get(path: str, params: dict) -> list | dict:
    """GET an OpenF1 endpoint. Its "no results" answer is ``404 {"detail": ...}``,
    not ``200 []`` — map that to NotFoundError so the chain reports NOT_FOUND
    instead of an outage. (404 is not retried by ``get_json_burst``.)
    """
    try:
        return await get_json_burst(f"{_OPENF1_BASE}/{path}", params=params)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise NotFoundError(f"OpenF1 has no {path} for {params}") from e
        raise


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
            # OpenF1's country_name filter is case-sensitive ("Monaco").
            params["country_name"] = country.strip().title()
        data = await _openf1_get("sessions", params)
        return {"sessions": data if isinstance(data, list) else [data]}

    async def healthcheck(self) -> bool:
        return True


class OpenF1DriversAdapter:
    name = "openf1"
    budget = None

    async def fetch(self, session_key: int, **kwargs) -> dict:
        data = await _openf1_get("drivers", {"session_key": session_key})
        drivers = data if isinstance(data, list) else [data]
        if not drivers:
            raise NotFoundError(f"OpenF1 returned no drivers for session_key={session_key}")
        return {"drivers": drivers}

    async def healthcheck(self) -> bool:
        return True


class OpenF1LapsAdapter:
    name = "openf1"
    budget = None

    async def fetch(self, session_key: int, driver_number: int, **kwargs) -> dict:
        data = await _openf1_get(
            "laps", {"session_key": session_key, "driver_number": driver_number}
        )
        laps = data if isinstance(data, list) else [data]
        if not laps:
            raise NotFoundError(
                f"OpenF1 returned no laps for session_key={session_key}, driver_number={driver_number}"
            )
        return {"laps": laps}

    async def healthcheck(self) -> bool:
        return True


class OpenF1StintsAdapter:
    name = "openf1"
    budget = None

    async def fetch(self, session_key: int, driver_number: int, **kwargs) -> dict:
        data = await _openf1_get(
            "stints", {"session_key": session_key, "driver_number": driver_number}
        )
        stints = data if isinstance(data, list) else [data]
        if not stints:
            raise NotFoundError(
                f"OpenF1 returned no stints for session_key={session_key}, driver_number={driver_number}"
            )
        return {"stints": stints}

    async def healthcheck(self) -> bool:
        return True


class OpenF1WeatherAdapter:
    name = "openf1"
    budget = None

    async def fetch(self, session_key: int, **kwargs) -> dict:
        data = await _openf1_get("weather", {"session_key": session_key})
        return {"weather": data if isinstance(data, list) else [data]}

    async def healthcheck(self) -> bool:
        return True
