"""OpenF1 adapter tests — all HTTP mocked with respx."""

from __future__ import annotations

import json
from pathlib import Path

import respx
from httpx import Response

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "openf1"


def _load(name: str) -> list | dict:
    return json.loads((_FIXTURES / name).read_text())


@respx.mock
async def test_openf1_sessions_adapter_returns_sessions():
    from sportiq.f1.adapters.openf1 import OpenF1SessionsAdapter

    respx.get("https://api.openf1.org/v1/sessions").mock(
        return_value=Response(200, json=_load("sessions_2025.json"))
    )
    result = await OpenF1SessionsAdapter().fetch(year=2025)
    assert "sessions" in result
    assert result["sessions"][0]["session_key"] == 9877
    assert result["sessions"][0]["country_name"] == "Monaco"


@respx.mock
async def test_openf1_drivers_adapter_returns_drivers():
    from sportiq.f1.adapters.openf1 import OpenF1DriversAdapter

    respx.get("https://api.openf1.org/v1/drivers").mock(
        return_value=Response(200, json=_load("drivers_session9877.json"))
    )
    result = await OpenF1DriversAdapter().fetch(session_key=9877)
    assert "drivers" in result
    assert result["drivers"][0]["driver_number"] == 1
    assert result["drivers"][0]["name_acronym"] == "VER"


@respx.mock
async def test_openf1_laps_adapter_returns_laps():
    from sportiq.f1.adapters.openf1 import OpenF1LapsAdapter

    respx.get("https://api.openf1.org/v1/laps").mock(
        return_value=Response(200, json=_load("laps_session9877.json"))
    )
    result = await OpenF1LapsAdapter().fetch(session_key=9877, driver_number=1)
    assert "laps" in result
    assert len(result["laps"]) == 2
    assert result["laps"][0]["lap_number"] == 1
    assert result["laps"][1]["lap_duration"] == 74.891


@respx.mock
async def test_openf1_stints_adapter_returns_stints():
    from sportiq.f1.adapters.openf1 import OpenF1StintsAdapter

    respx.get("https://api.openf1.org/v1/stints").mock(
        return_value=Response(200, json=_load("stints_session9877.json"))
    )
    result = await OpenF1StintsAdapter().fetch(session_key=9877, driver_number=1)
    assert "stints" in result
    assert result["stints"][0]["compound"] == "SOFT"
    assert result["stints"][0]["lap_end"] == 20


@respx.mock
async def test_openf1_weather_adapter_returns_weather():
    from sportiq.f1.adapters.openf1 import OpenF1WeatherAdapter

    respx.get("https://api.openf1.org/v1/weather").mock(
        return_value=Response(200, json=_load("weather_session9877.json"))
    )
    result = await OpenF1WeatherAdapter().fetch(session_key=9877)
    assert "weather" in result
    assert result["weather"][0]["air_temperature"] == 22.5
    assert result["weather"][0]["rainfall"] == 0
