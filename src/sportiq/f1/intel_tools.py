"""F1 INTEL tools — Phase 3 flagship layer.

Five tools composing chains + models into actionable strategy answers.
Flagship: f1_predict_pit_strategy.
"""
from __future__ import annotations

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.tool_response import error_envelope
from sportiq.f1.chains import f1_laps_chain, f1_stints_chain, f1_weather_chain
from sportiq.f1.models.pit_strategy import predict as _predict_strategy
from sportiq.f1.models.tyre_deg import fit_degradation
from sportiq.f1.models.undercut import undercut_window


async def f1_tyre_degradation(session_key: int, driver_number: int, compound: str) -> dict:
    """Fit a tyre degradation model for a driver + compound in a session.

    Args:
        session_key: OpenF1 session identifier.
        driver_number: Driver's race number.
        compound: Tyre compound (SOFT, MEDIUM, HARD, INTER, WET).

    Returns:
        data: {intercept, slope, residual_std, sample_count}.
        meta.estimated: true — model output, not telemetry oracle.
    """
    if session_key <= 0 or driver_number <= 0:
        return error_envelope(
            code="INVALID_INPUT",
            message="session_key and driver_number must be positive.",
        )
    compound_upper = compound.upper()
    if compound_upper not in {"SOFT", "MEDIUM", "HARD", "INTER", "WET"}:
        return error_envelope(
            code="INVALID_INPUT",
            message="compound must be SOFT, MEDIUM, HARD, INTER, or WET.",
        )

    try:
        laps_result = await f1_laps_chain.fetch(session_key=session_key, driver_number=driver_number)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch lap data.",
            sources_tried=e.attempts,
        )

    model = fit_degradation(laps_result.value.get("laps", []), compound_upper)
    return {
        "data": model,
        "meta": {
            "source": laps_result.source,
            "session_key": session_key,
            "driver_number": driver_number,
            "compound": compound_upper,
            "estimated": True,
        },
    }


async def f1_undercut_window(
    session_key: int,
    attacker_number: int,
    target_number: int,
    current_lap: int,
) -> dict:
    """Estimate whether an undercut is viable for the attacker against the target.

    Args:
        session_key: OpenF1 session identifier.
        attacker_number: Attacking driver's race number.
        target_number: Target driver's race number.
        current_lap: Current lap number in the race.

    Returns:
        data: {laps_to_clear, viable, marginal}.
        meta.estimated: true.
    """
    if session_key <= 0 or attacker_number <= 0 or target_number <= 0 or current_lap <= 0:
        return error_envelope(
            code="INVALID_INPUT",
            message="All numeric args must be positive.",
        )

    try:
        attacker_laps = await f1_laps_chain.fetch(session_key=session_key, driver_number=attacker_number)
        target_laps = await f1_laps_chain.fetch(session_key=session_key, driver_number=target_number)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch lap data.",
            sources_tried=e.attempts,
        )

    def _recent_pace(laps_payload: dict) -> float:
        laps = laps_payload.get("laps", [])
        recent = [lap["lap_duration"] for lap in laps[-5:] if lap.get("lap_duration")]
        return sum(recent) / len(recent) if recent else 83.0

    attacker_pace = _recent_pace(attacker_laps.value)
    target_pace = _recent_pace(target_laps.value)

    # Default pit loss and fresh-tyre delta — circuit-specific tuning in Phase 3.1
    result = undercut_window(
        driver_pace_s=attacker_pace,
        target_pace_s=target_pace,
        pit_loss_s=22.0,
        fresh_tyre_delta_s=1.5,
        gap_to_target_s=2.0,
    )
    return {
        "data": result,
        "meta": {
            "source": attacker_laps.source,
            "estimated": True,
            "attacker": attacker_number,
            "target": target_number,
        },
    }


async def f1_head_to_head_pace(session_key: int, driver_a: int, driver_b: int) -> dict:
    """Compare lap-time pace distribution between two drivers in a session.

    Args:
        session_key: OpenF1 session identifier.
        driver_a: First driver's race number.
        driver_b: Second driver's race number.

    Returns:
        data: {driver_a_avg_s, driver_b_avg_s, delta_s, faster_driver}.
        meta.estimated: true.
    """
    if session_key <= 0 or driver_a <= 0 or driver_b <= 0:
        return error_envelope(code="INVALID_INPUT", message="All args must be positive.")

    try:
        laps_a = await f1_laps_chain.fetch(session_key=session_key, driver_number=driver_a)
        laps_b = await f1_laps_chain.fetch(session_key=session_key, driver_number=driver_b)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch lap data.",
            sources_tried=e.attempts,
        )

    def _avg(payload: dict) -> float | None:
        laps = [lap["lap_duration"] for lap in payload.get("laps", []) if lap.get("lap_duration")]
        return round(sum(laps) / len(laps), 3) if laps else None

    avg_a = _avg(laps_a.value)
    avg_b = _avg(laps_b.value)
    delta = round(avg_a - avg_b, 3) if avg_a is not None and avg_b is not None else None
    faster = driver_a if delta is not None and delta < 0 else (driver_b if delta is not None else None)

    return {
        "data": {
            "driver_a_avg_s": avg_a,
            "driver_b_avg_s": avg_b,
            "delta_s": delta,
            "faster_driver": faster,
        },
        "meta": {"source": laps_a.source, "estimated": True},
    }


async def f1_weather_strategy_impact(session_key: int) -> dict:
    """Analyse weather data and recommend compound or pit-window adjustments.

    Args:
        session_key: OpenF1 session identifier.

    Returns:
        data: {has_rain, avg_track_temp_c, compound_recommendation, recommendation}.
        meta.estimated: true.
    """
    if session_key <= 0:
        return error_envelope(code="INVALID_INPUT", message="session_key must be positive.")

    try:
        weather_result = await f1_weather_chain.fetch(session_key=session_key)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch weather data.",
            sources_tried=e.attempts,
        )

    weather = weather_result.value.get("weather", [])
    has_rain = any(float(w.get("rainfall", 0)) > 0 for w in weather)
    temps = [float(w["track_temperature"]) for w in weather if w.get("track_temperature") is not None]
    avg_temp = round(sum(temps) / len(temps), 1) if temps else None

    if has_rain:
        compound_rec = "INTER"
        recommendation = "Switch to intermediate tyres immediately — rainfall detected."
    elif avg_temp is not None and avg_temp > 45:
        compound_rec = "HARD"
        recommendation = f"High track temperature ({avg_temp}°C) — prefer HARD to reduce thermal degradation."
    elif avg_temp is not None and avg_temp < 25:
        compound_rec = "SOFT"
        recommendation = f"Cool track ({avg_temp}°C) — SOFT tyres will reach operating temperature faster."
    else:
        compound_rec = "MEDIUM"
        recommendation = "Nominal conditions — MEDIUM is the baseline choice."

    return {
        "data": {
            "has_rain": has_rain,
            "avg_track_temp_c": avg_temp,
            "compound_recommendation": compound_rec,
            "recommendation": recommendation,
        },
        "meta": {"source": weather_result.source, "estimated": True},
    }


async def f1_predict_pit_strategy(
    session_key: int,
    driver_number: int,
    current_lap: int = 1,
    total_laps: int = 57,
) -> dict:
    """Predict the optimal pit-stop strategy for a driver in an F1 race session.

    Args:
        session_key: OpenF1 session identifier for a recorded race.
        driver_number: Driver's race number (e.g. 1 for Verstappen).
        current_lap: Current lap to project from (default 1 = full race ahead).
        total_laps: Total race laps (default 57; pulled from session metadata if available).

    Returns:
        data.stop_laps: recommended pit laps.
        data.compound_sequence: tyre compounds for each stint.
        data.expected_finish_position: None (modelled in Phase 4).
        data.confidence: 0.0-1.0 model confidence.
        meta.estimated: true.
    """
    if session_key <= 0 or driver_number <= 0:
        return error_envelope(
            code="INVALID_INPUT",
            message="session_key and driver_number must be positive.",
        )
    if current_lap < 1 or total_laps < current_lap:
        return error_envelope(
            code="INVALID_INPUT",
            message="current_lap must be >= 1 and <= total_laps.",
        )

    try:
        laps_result = await f1_laps_chain.fetch(session_key=session_key, driver_number=driver_number)
        stints_result = await f1_stints_chain.fetch(session_key=session_key, driver_number=driver_number)
        weather_result = await f1_weather_chain.fetch(session_key=session_key)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch required data for pit strategy prediction.",
            sources_tried=e.attempts,
        )

    strategy = _predict_strategy(
        laps=laps_result.value.get("laps", []),
        stints=stints_result.value.get("stints", []),
        weather=weather_result.value.get("weather", []),
        current_lap=current_lap,
        total_laps=total_laps,
    )
    return {
        "data": strategy,
        "meta": {
            "source": laps_result.source,
            "session_key": session_key,
            "driver_number": driver_number,
            "estimated": True,
        },
    }


def register_f1_intel_tools(mcp) -> None:
    """Register the five F1 INTEL tools on the supplied FastMCP instance."""
    mcp.tool()(f1_tyre_degradation)
    mcp.tool()(f1_undercut_window)
    mcp.tool()(f1_head_to_head_pace)
    mcp.tool()(f1_weather_strategy_impact)
    mcp.tool()(f1_predict_pit_strategy)
