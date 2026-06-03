"""Qualifying analysis — best lap per driver, gap to pole, grid projection.

Pure functions, no I/O.
"""
from __future__ import annotations


def best_lap_per_driver(laps: list[dict]) -> dict[str, float]:
    """Extract best (minimum) lap_duration per driver_number from laps list.

    Args:
        laps: list of lap dicts from OpenF1 /laps (driver_number, lap_duration).

    Returns:
        {driver_number_str: best_lap_seconds} — only drivers with valid laps.
    """
    bests: dict[str, float] = {}
    for lap in laps:
        dn = str(lap.get("driver_number", ""))
        dur = lap.get("lap_duration")
        if dur is None or not dn:
            continue
        try:
            dur_f = float(dur)
        except (TypeError, ValueError):
            continue
        if dur_f <= 0:
            continue
        if dn not in bests or dur_f < bests[dn]:
            bests[dn] = dur_f
    return bests


def gap_to_pole(best_laps: dict[str, float]) -> dict[str, float]:
    """Compute gap (seconds) from each driver's best lap to the pole time.

    Returns {driver_number_str: gap_seconds} sorted by gap ascending.
    Pole time = minimum best lap. Pole driver has gap 0.0.
    """
    if not best_laps:
        return {}
    pole_time = min(best_laps.values())
    gaps = {dn: round(t - pole_time, 3) for dn, t in best_laps.items()}
    return dict(sorted(gaps.items(), key=lambda x: x[1]))


def grid_projection(
    gaps: dict[str, float],
    driver_info: dict[str, dict],
) -> list[dict]:
    """Build a projected grid from gap-to-pole order.

    Args:
        gaps: {driver_number_str: gap_seconds} from gap_to_pole(), already sorted.
        driver_info: {driver_number_str: {full_name, team_name, ...}} from OpenF1 /drivers.

    Returns:
        list of {position, driver_number, full_name, team_name, best_lap_gap_s},
        sorted by position ascending.
    """
    grid = []
    for pos, (dn, gap) in enumerate(gaps.items(), start=1):
        info = driver_info.get(dn, {})
        grid.append(
            {
                "position": pos,
                "driver_number": int(dn) if dn.isdigit() else dn,
                "full_name": info.get("full_name", f"Driver #{dn}"),
                "team_name": info.get("team_name", "Unknown"),
                "best_lap_gap_s": gap,
            }
        )
    return grid
