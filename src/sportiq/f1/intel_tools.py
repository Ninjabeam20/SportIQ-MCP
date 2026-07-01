"""F1 INTEL tools — Phase 3 flagship layer.

Five tools composing chains + models into actionable strategy answers.
Flagship: f1_predict_pit_strategy.
"""
from __future__ import annotations

import asyncio

from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.tool_response import Envelope, error_envelope, staleness_meta
from sportiq.f1.chains import (
    f1_drivers_chain,
    f1_laps_chain,
    f1_session_meta_chain,
    f1_stints_chain,
    f1_weather_chain,
)
from sportiq.f1.circuits import profile_for_circuit_key
from sportiq.f1.models.pit_strategy import _DEFAULT_PIT_LOSS_S
from sportiq.f1.models.pit_strategy import predict as _predict_strategy
from sportiq.f1.models.quali_analysis import best_lap_per_driver, gap_to_pole, grid_projection
from sportiq.f1.models.race_pace import compare_race_pace
from sportiq.f1.models.tyre_deg import annotate_laps_with_stints, fit_degradation
from sportiq.f1.models.undercut import undercut_window

# Cap concurrent per-driver lap fetches. When asyncio.gather fan-out is added
# later (e.g. fetching laps for all 20 drivers in parallel), this semaphore
# ensures at most 5 in-flight requests hit OpenF1 at once.
_F1_LAP_SEMAPHORE = asyncio.Semaphore(5)


async def _fetch_driver_laps(session_key: int, driver_number: int):
    """Fetch laps for one driver, gated by the per-driver concurrency cap."""
    async with _F1_LAP_SEMAPHORE:
        return await f1_laps_chain.fetch(session_key=session_key, driver_number=driver_number)


async def _resolve_circuit_profile(session_key: int) -> dict | None:
    """Best-effort: resolve a session's circuit and return its measured profile.

    Looks up the session's ``circuit_key`` (cached 6h) and maps it to the F1DB
    pit-loss profile. Returns None on any failure or unknown circuit — the caller
    falls back to the generic pit-loss default, never erroring on enrichment.
    """
    try:
        meta = await f1_session_meta_chain.fetch(session_key=session_key)
    except (AllSourcesFailedError, NotFoundError):
        # NotFoundError fires when the session_key resolves to nothing; both are
        # enrichment failures the caller treats as "no profile", never a 500.
        return None
    sessions = meta.value.get("sessions", [])
    if not sessions:
        return None
    return profile_for_circuit_key(sessions[0].get("circuit_key"))


async def f1_tyre_degradation(session_key: int, driver_number: int, compound: str) -> Envelope:
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

    # OpenF1 /laps carries no compound/tyre_life — those live on /stints, which we
    # merge in to enrich the fit. Laps are required; stint enrichment is
    # *best-effort*: if the stints source is down we still fit on whatever the
    # laps already carry (e.g. fastf1 laps), so a stints outage degrades quality
    # rather than failing the call. The two chains are independent — gather them.
    laps_r, stints_r = await asyncio.gather(
        f1_laps_chain.fetch(session_key=session_key, driver_number=driver_number),
        f1_stints_chain.fetch(session_key=session_key, driver_number=driver_number),
        return_exceptions=True,
    )
    if isinstance(laps_r, AllSourcesFailedError):
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch lap data.",
            sources_tried=laps_r.attempts,
        )
    if isinstance(laps_r, BaseException):
        raise laps_r
    laps_result = laps_r

    stints: list[dict] = []
    stints_result = None
    if isinstance(stints_r, AllSourcesFailedError):
        pass
    elif isinstance(stints_r, BaseException):
        raise stints_r
    else:
        stints_result = stints_r
        stints = stints_result.value.get("stints", [])

    annotated = annotate_laps_with_stints(laps_result.value.get("laps", []), stints)
    model = fit_degradation(annotated, compound_upper)
    sources = [laps_result] + ([stints_result] if stints_result is not None else [])
    return {
        "data": model,
        "meta": {
            "source": laps_result.source,
            "session_key": session_key,
            "driver_number": driver_number,
            "compound": compound_upper,
            "estimated": True,
            "stint_enrichment": stints_result is not None,
            **staleness_meta(*sources),
        },
    }


async def f1_undercut_window(
    session_key: int,
    attacker_number: int,
    target_number: int,
    current_lap: int,
) -> Envelope:
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
        # _resolve_circuit_profile is best-effort (never raises) so it rides the
        # same gather as the lap fetches — one round-trip, not a serial follow-up.
        attacker_laps, target_laps, profile = await asyncio.gather(
            _fetch_driver_laps(session_key=session_key, driver_number=attacker_number),
            _fetch_driver_laps(session_key=session_key, driver_number=target_number),
            _resolve_circuit_profile(session_key),
        )
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

    # Measured per-circuit pit loss (F1DB) when the circuit resolves; else the
    # generic 22.0s default. fresh_tyre_delta stays a generic estimate (F1DB
    # carries no tyre-delta data).
    pit_loss_s = profile["pit_loss_s"] if profile else _DEFAULT_PIT_LOSS_S

    result = undercut_window(
        driver_pace_s=attacker_pace,
        target_pace_s=target_pace,
        pit_loss_s=pit_loss_s,
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
            "pit_loss_s": pit_loss_s,
            "circuit_profile": profile is not None,
            "circuit": profile["circuit"] if profile else None,
            **staleness_meta(attacker_laps, target_laps),
        },
    }


async def f1_head_to_head_pace(session_key: int, driver_a: int, driver_b: int) -> Envelope:
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
        laps_a, laps_b = await asyncio.gather(
            _fetch_driver_laps(session_key=session_key, driver_number=driver_a),
            _fetch_driver_laps(session_key=session_key, driver_number=driver_b),
        )
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
    # None when there's no comparable data or the pace is an exact tie (delta == 0).
    faster = None if not delta else (driver_a if delta < 0 else driver_b)

    return {
        "data": {
            "driver_a_avg_s": avg_a,
            "driver_b_avg_s": avg_b,
            "delta_s": delta,
            "faster_driver": faster,
        },
        "meta": {
            "source": laps_a.source,
            "estimated": True,
            **staleness_meta(laps_a, laps_b),
        },
    }


async def f1_weather_strategy_impact(session_key: int) -> Envelope:
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
        "meta": {
            "source": weather_result.source,
            "estimated": True,
            **staleness_meta(weather_result),
        },
    }


async def f1_predict_pit_strategy(
    session_key: int,
    driver_number: int,
    current_lap: int = 1,
    total_laps: int | None = None,
) -> Envelope:
    """Predict the optimal pit-stop strategy for a driver in an F1 race session.

    Args:
        session_key: OpenF1 session identifier for a recorded race.
        driver_number: Driver's race number (e.g. 1 for Verstappen).
        current_lap: Current lap to project from (default 1 = full race ahead).
        total_laps: Total race laps. If omitted, inferred from the highest
            observed lap_number in the fetched laps (correct for Monaco 78 /
            Spa 44), falling back to 57 when no laps are available. An explicit
            value always wins.

    Returns:
        data.stop_laps: recommended pit laps.
        data.compound_sequence: tyre compounds for each stint.
        data.expected_finish_position: currently always None (not modelled).
        data.confidence: 0.0-1.0 model confidence.
        meta.total_laps: race length used (explicit arg, else inferred from laps).
        meta.estimated: true.

    Example:
        f1_predict_pit_strategy(session_key=9158, driver_number=1)
        f1_predict_pit_strategy(session_key=9158, driver_number=16, current_lap=20, total_laps=78)
    """
    if session_key <= 0 or driver_number <= 0:
        return error_envelope(
            code="INVALID_INPUT",
            message="session_key and driver_number must be positive.",
        )
    if current_lap < 1 or (total_laps is not None and total_laps < current_lap):
        return error_envelope(
            code="INVALID_INPUT",
            message="current_lap must be >= 1 and <= total_laps.",
        )

    # Laps are required; stints + weather are best-effort enrichment. If either
    # enrichment source is down the model still runs (the pit_strategy model
    # falls back to TyreSpec constants and dry-weather assumptions), so we
    # degrade quality rather than 500-ing. All three chains are independent —
    # gather them instead of paying three serial round-trips.
    laps_r, stints_r, weather_r, profile = await asyncio.gather(
        f1_laps_chain.fetch(session_key=session_key, driver_number=driver_number),
        f1_stints_chain.fetch(session_key=session_key, driver_number=driver_number),
        f1_weather_chain.fetch(session_key=session_key),
        _resolve_circuit_profile(session_key),  # best-effort, never raises
        return_exceptions=True,
    )
    if isinstance(laps_r, AllSourcesFailedError):
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch lap data for pit strategy prediction.",
            sources_tried=laps_r.attempts,
        )
    if isinstance(laps_r, BaseException):
        raise laps_r
    laps_result = laps_r

    stints: list[dict] = []
    stints_result = None
    if isinstance(stints_r, AllSourcesFailedError):
        pass
    elif isinstance(stints_r, BaseException):
        raise stints_r
    else:
        stints_result = stints_r
        stints = stints_result.value.get("stints", [])

    weather: list[dict] = []
    weather_result = None
    if isinstance(weather_r, AllSourcesFailedError):
        pass
    elif isinstance(weather_r, BaseException):
        raise weather_r
    else:
        weather_result = weather_r
        weather = weather_result.value.get("weather", [])

    laps = laps_result.value.get("laps", [])
    # Caller left total_laps unset → infer from the highest observed lap_number
    # (the flagship already fetched the laps); fall back to 57 if none carry one.
    if total_laps is None:
        observed = [n for lap in laps if (n := lap.get("lap_number")) and n > 0]
        total_laps = max(observed) if observed else 57

    # Measured per-circuit pit loss when resolvable; else the model default.
    # gather may hand back an exception here — treat anything non-dict as "unknown".
    circuit = profile if isinstance(profile, dict) else None
    pit_loss_s = circuit["pit_loss_s"] if circuit else _DEFAULT_PIT_LOSS_S

    # Annotate laps with compound/tyre_life from /stints so the degradation fit
    # uses telemetry instead of silently falling back to TyreSpec constants.
    annotated = annotate_laps_with_stints(laps, stints)
    strategy = _predict_strategy(
        laps=annotated,
        stints=stints,
        weather=weather,
        current_lap=current_lap,
        total_laps=total_laps,
        pit_loss_s=pit_loss_s,
    )
    sources = [r for r in (laps_result, stints_result, weather_result) if r is not None]
    return {
        "data": strategy,
        "meta": {
            "source": laps_result.source,
            "session_key": session_key,
            "driver_number": driver_number,
            "total_laps": total_laps,
            "estimated": True,
            "stint_enrichment": stints_result is not None,
            "weather_enrichment": weather_result is not None,
            "pit_loss_s": pit_loss_s,
            "circuit_profile": circuit is not None,
            "circuit": circuit["circuit"] if circuit else None,
            **staleness_meta(*sources),
        },
    }


async def f1_qualifying_analysis(session_key: int) -> Envelope:
    """Analyse a qualifying session: best lap per driver, gap to pole, projected grid.

    Args:
        session_key: OpenF1 session identifier for a Qualifying session.

    Returns:
        data.grid: [{position, driver_number, full_name, team_name, best_lap_gap_s}].
        data.pole_time_s: pole lap duration in seconds.
        data.drivers_analysed: count of drivers with valid laps.
        meta.estimated: true — grid derived from session laps, not official timing.
    """
    if session_key <= 0:
        return error_envelope(code="INVALID_INPUT", message="session_key must be positive.")

    try:
        drivers_result = await f1_drivers_chain.fetch(session_key=session_key)
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message=f"Could not fetch drivers for session {session_key}.",
            sources_tried=e.attempts,
        )
    except NotFoundError:
        return error_envelope(
            code="NOT_FOUND",
            message=f"No drivers found for session {session_key}.",
        )

    driver_list = drivers_result.value.get("drivers", [])
    driver_info = {
        str(d.get("driver_number", "")): d
        for d in driver_list
        if d.get("driver_number")
    }

    tasks = [
        _fetch_driver_laps(session_key, int(dn))
        for dn in driver_info
        if dn.isdigit()
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_laps: list[dict] = []
    for res in raw_results:
        if isinstance(res, Exception):
            continue
        all_laps.extend(res.value.get("laps", []))

    bests = best_lap_per_driver(all_laps)
    gaps = gap_to_pole(bests)
    grid = grid_projection(gaps, driver_info)
    pole_time = min(bests.values()) if bests else None

    successful_lap_results = [r for r in raw_results if not isinstance(r, Exception)]
    all_results = [drivers_result, *successful_lap_results]
    return {
        "data": {
            "session_key": session_key,
            "grid": grid,
            "pole_time_s": round(pole_time, 3) if pole_time is not None else None,
            "drivers_analysed": len(bests),
        },
        "meta": {
            "source": drivers_result.source,
            "estimated": True,
            **staleness_meta(*all_results),
        },
    }


async def f1_race_pace_compare(session_key: int, driver_a: int, driver_b: int) -> Envelope:
    """Compare race-pace and tyre degradation between two F1 drivers in a session.

    Args:
        session_key: OpenF1 session identifier.
        driver_a: First driver's race number.
        driver_b: Second driver's race number.

    Returns:
        data: {by_compound, overall_faster, compounds_compared}.
        meta.estimated: true — degradation model fit, not official timing.
    """
    if session_key <= 0 or driver_a <= 0 or driver_b <= 0:
        return error_envelope(code="INVALID_INPUT", message="All args must be positive.")
    if driver_a == driver_b:
        return error_envelope(code="INVALID_INPUT", message="driver_a and driver_b must differ.")

    laps_a_r, stints_a_r, laps_b_r, stints_b_r = await asyncio.gather(
        _fetch_driver_laps(session_key, driver_a),
        f1_stints_chain.fetch(session_key=session_key, driver_number=driver_a),
        _fetch_driver_laps(session_key, driver_b),
        f1_stints_chain.fetch(session_key=session_key, driver_number=driver_b),
        return_exceptions=True,
    )

    # Laps are required; stints are best-effort
    if isinstance(laps_a_r, Exception) or isinstance(laps_b_r, Exception):
        attempts = []
        for exc in (laps_a_r, laps_b_r):
            if isinstance(exc, AllSourcesFailedError):
                attempts.extend(exc.attempts)
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="Could not fetch lap data for one or both drivers.",
            sources_tried=attempts,
        )

    laps_a = laps_a_r.value.get("laps", [])
    stints_a = stints_a_r.value.get("stints", []) if not isinstance(stints_a_r, Exception) else []
    laps_b = laps_b_r.value.get("laps", [])
    stints_b = stints_b_r.value.get("stints", []) if not isinstance(stints_b_r, Exception) else []

    result = compare_race_pace(laps_a, stints_a, laps_b, stints_b, driver_a, driver_b)
    return {
        "data": result,
        "meta": {
            "source": laps_a_r.source,
            "estimated": True,
            **staleness_meta(laps_a_r, laps_b_r),
        },
    }


def register_f1_intel_tools(mcp) -> None:
    """Register all F1 INTEL tools on the supplied FastMCP instance."""
    from sportiq.core.tool_meta import READ_ONLY

    mcp.tool(annotations=READ_ONLY)(f1_tyre_degradation)
    mcp.tool(annotations=READ_ONLY)(f1_undercut_window)
    mcp.tool(annotations=READ_ONLY)(f1_head_to_head_pace)
    mcp.tool(annotations=READ_ONLY)(f1_weather_strategy_impact)
    mcp.tool(annotations=READ_ONLY)(f1_predict_pit_strategy)
    mcp.tool(annotations=READ_ONLY)(f1_qualifying_analysis)
    mcp.tool(annotations=READ_ONLY)(f1_race_pace_compare)
