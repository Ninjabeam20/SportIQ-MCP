"""F1 RAW tools — Phase 3.

Thin wrappers: validate args → call chain.fetch() → return tool_response.
"""
from __future__ import annotations

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.tool_response import error_envelope, tool_response
from sportiq.f1.chains import (
    f1_drivers_chain,
    f1_laps_chain,
    f1_sessions_chain,
    f1_standings_chain,
    f1_weather_chain,
)


async def f1_get_sessions(year: int, country: str | None = None) -> dict:
    """Return F1 sessions for a given year, optionally filtered by country.

    Args:
        year: Championship year (e.g. 2025).
        country: Optional country name to filter (e.g. "Monaco").

    Returns:
        data.sessions: list of session objects with session_key, session_type, date.
        meta.source: adapter that served the data.
    """
    if year < 2018 or year > 2030:
        return error_envelope(code="INVALID_INPUT", message="year must be between 2018 and 2030.")
    try:
        result = await f1_sessions_chain.fetch(year=year, country=country)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch F1 sessions for year {year}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def f1_get_drivers(session_key: int) -> dict:
    """Return driver list for a specific F1 session.

    Args:
        session_key: OpenF1 session identifier.

    Returns:
        data.drivers: list of driver objects with driver_number, full_name, team.
        meta.source: adapter that served the data.
    """
    if session_key <= 0:
        return error_envelope(code="INVALID_INPUT", message="session_key must be positive.")
    try:
        result = await f1_drivers_chain.fetch(session_key=session_key)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch drivers for session {session_key}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def f1_get_lap_times(session_key: int, driver_number: int) -> dict:
    """Return lap times for a driver in a specific F1 session.

    Args:
        session_key: OpenF1 session identifier.
        driver_number: Driver's race number (e.g. 1 for Verstappen).

    Returns:
        data.laps: list of lap objects with lap_number, lap_duration, compound.
        meta.source: adapter that served the data.
    """
    if session_key <= 0:
        return error_envelope(code="INVALID_INPUT", message="session_key must be positive.")
    if driver_number <= 0 or driver_number > 99:
        return error_envelope(code="INVALID_INPUT", message="driver_number must be 1-99.")
    try:
        result = await f1_laps_chain.fetch(session_key=session_key, driver_number=driver_number)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch laps for driver {driver_number} in session {session_key}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def f1_get_standings(year: int) -> dict:
    """Return F1 driver and constructor championship standings for a year.

    Args:
        year: Championship year (e.g. 2025).

    Returns:
        data.driver_standings: driver championship positions and points.
        data.constructor_standings: constructor championship positions and points.
        meta.source: adapter that served the data.
    """
    if year < 2018 or year > 2030:
        return error_envelope(code="INVALID_INPUT", message="year must be between 2018 and 2030.")
    try:
        result = await f1_standings_chain.fetch(year=year)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch F1 standings for {year}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def f1_get_race_results(session_key: int) -> dict:
    """Return race results for a specific F1 session (lap times + final order proxy).

    Args:
        session_key: OpenF1 session identifier.

    Returns:
        data.laps: lap data for all available drivers (proxy for race results).
        meta.source: adapter that served the data.
    """
    if session_key <= 0:
        return error_envelope(code="INVALID_INPUT", message="session_key must be positive.")
    try:
        result = await f1_drivers_chain.fetch(session_key=session_key)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch race results for session {session_key}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def f1_get_weather(session_key: int) -> dict:
    """Return weather data for a specific F1 session.

    Args:
        session_key: OpenF1 session identifier.

    Returns:
        data.weather: list of weather snapshots with temperature, rainfall, wind.
        meta.source: adapter that served the data.
    """
    if session_key <= 0:
        return error_envelope(code="INVALID_INPUT", message="session_key must be positive.")
    try:
        result = await f1_weather_chain.fetch(session_key=session_key)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch weather for session {session_key}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


def register_f1_tools(mcp) -> None:
    """Register all F1 tools on the supplied FastMCP instance."""
    from sportiq.f1.intel_tools import register_f1_intel_tools

    mcp.tool()(f1_get_sessions)
    mcp.tool()(f1_get_drivers)
    mcp.tool()(f1_get_lap_times)
    mcp.tool()(f1_get_standings)
    mcp.tool()(f1_get_race_results)
    mcp.tool()(f1_get_weather)
    register_f1_intel_tools(mcp)
