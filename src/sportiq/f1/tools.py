"""F1 RAW tools — Phase 3.

Thin wrappers: validate args → call chain.fetch() → return tool_response.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.tool_response import Envelope, error_envelope, paginate, tool_response
from sportiq.f1.chains import (
    f1_drivers_chain,
    f1_laps_chain,
    f1_results_chain,
    f1_sessions_chain,
    f1_standings_chain,
    f1_weather_chain,
)


def _session_end(session: dict) -> datetime | None:
    raw = session.get("date_end")
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


async def f1_get_sessions(
    year: int,
    country: str | None = None,
    session_name: str | None = None,
    latest_completed: bool = False,
) -> Envelope:
    """Return F1 sessions for a given year, optionally filtered by country or session name.

    Args:
        year: Championship year (e.g. 2026).
        country: Optional country name to filter (e.g. "Netherlands").
        session_name: Optional session name to keep, case-insensitive (e.g. "Race",
            "Qualifying", "Sprint").
        latest_completed: When true, return only the single session that ended most
            recently (greatest date_end before now, UTC) — e.g. with
            session_name="Race", the latest finished Grand Prix.

    Returns:
        data.sessions: list of session objects with session_key, session_type, date.
        meta.source: adapter that served the data.
    """
    if year < 2018 or year > 2030:
        return error_envelope(code="INVALID_INPUT", message="year must be between 2018 and 2030.")
    try:
        result = await f1_sessions_chain.fetch(year=year, country=country)
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(
            code=e.code,
            message=f"Could not fetch F1 sessions for year {year}.",
            sources_tried=e.attempts,
        )
    # Filter after the chain fetch so cache keys stay year/country only.
    if session_name is not None or latest_completed:
        sessions = result.value.get("sessions", [])
        if session_name is not None:
            wanted = session_name.strip().lower()
            sessions = [s for s in sessions if str(s.get("session_name", "")).lower() == wanted]
        if latest_completed:
            now = datetime.now(UTC)
            ended = [(end, s) for s in sessions if (end := _session_end(s)) and end < now]
            sessions = [max(ended, key=lambda pair: pair[0])[1]] if ended else []
        result.value = {**result.value, "sessions": sessions}
    return tool_response(result)


async def f1_get_drivers(session_key: int) -> Envelope:
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
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(
            code=e.code,
            message=f"Could not fetch drivers for session {session_key}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def f1_get_lap_times(
    session_key: int, driver_number: int, limit: int = 100, offset: int = 0
) -> Envelope:
    """Return lap times for a driver in a specific F1 session.

    Args:
        session_key: OpenF1 session identifier.
        driver_number: Driver's race number (driver numbers change by season; use f1_get_drivers).
        limit: Max laps to return, 1..200 (default 100 — covers most full races).
        offset: Number of laps to skip for paging (default 0).

    Returns:
        data.laps: page of lap objects with lap_number and lap_duration. OpenF1
            does not put compound/tyre_life here — those live on the stints endpoint.
        data.pagination: {total, count, offset, limit, has_more, next_offset}.
        meta.source: adapter that served the data.
    """
    if session_key <= 0:
        return error_envelope(code="INVALID_INPUT", message="session_key must be positive.")
    if driver_number <= 0 or driver_number > 99:
        return error_envelope(code="INVALID_INPUT", message="driver_number must be 1-99.")
    if not 1 <= limit <= 200:
        return error_envelope(code="INVALID_INPUT", message="limit must be in [1, 200].")
    if offset < 0:
        return error_envelope(code="INVALID_INPUT", message="offset must be >= 0.")
    try:
        result = await f1_laps_chain.fetch(session_key=session_key, driver_number=driver_number)
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(
            code=e.code,
            message=f"Could not fetch laps for driver {driver_number} in session {session_key}.",
            sources_tried=e.attempts,
        )
    result.value = paginate(result.value, "laps", limit, offset)
    return tool_response(result)


async def f1_get_standings(year: int) -> Envelope:
    """Return F1 driver and constructor championship standings for a year.

    Use this for "who is leading / who will win the F1 championship this year".
    For title probabilities use f1_simulate_championship.
    This is not a cricket or football tool.

    Args:
        year: Championship year (e.g. 2026).

    Returns:
        data.season / data.round: season and the last round counted.
        data.drivers: [{position, driver_number, code, name, team, points, wins}]
            (points are season totals).
        data.constructors: [{position, team, points, wins}].
        Same shape from every source (Jolpica primary; the FastF1 fallback
        sums per-race points and omits sprint points).
        meta.source: adapter that served the data.
    """
    if year < 2018 or year > 2030:
        return error_envelope(code="INVALID_INPUT", message="year must be between 2018 and 2030.")
    try:
        result = await f1_standings_chain.fetch(year=year)
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(
            code=e.code,
            message=f"Could not fetch F1 standings for {year}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def f1_get_race_results(year: int, round: int) -> Envelope:
    """Return the final classification for one F1 race, keyed by year and round.

    Args:
        year: Championship year (e.g. 2025).
        round: Round number within the season (1-based; e.g. 1 for the opener).

    Returns:
        data.results: Ergast/Jolpica RaceTable payload — finishing order, times,
            grid positions, points, and fastest laps for the race.
        meta.source: adapter that served the data.
    """
    if year < 2018 or year > 2030:
        return error_envelope(code="INVALID_INPUT", message="year must be between 2018 and 2030.")
    if round < 1 or round > 30:
        return error_envelope(code="INVALID_INPUT", message="round must be between 1 and 30.")
    try:
        result = await f1_results_chain.fetch(year=year, round=round)
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(
            code=e.code,
            message=f"Could not fetch race results for {year} round {round}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


async def f1_get_weather(session_key: int) -> Envelope:
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
    except (AllSourcesFailedError, NotFoundError) as e:
        return error_envelope(
            code=e.code,
            message=f"Could not fetch weather for session {session_key}.",
            sources_tried=e.attempts,
        )
    return tool_response(result)


def register_f1_tools(mcp) -> None:
    """Register all F1 tools on the supplied FastMCP instance."""
    from sportiq.core.tool_meta import READ_ONLY
    from sportiq.f1.intel_tools import register_f1_intel_tools

    mcp.tool(annotations=READ_ONLY)(f1_get_sessions)
    mcp.tool(annotations=READ_ONLY)(f1_get_drivers)
    mcp.tool(annotations=READ_ONLY)(f1_get_lap_times)
    mcp.tool(annotations=READ_ONLY)(f1_get_standings)
    mcp.tool(annotations=READ_ONLY)(f1_get_race_results)
    mcp.tool(annotations=READ_ONLY)(f1_get_weather)
    register_f1_intel_tools(mcp)
