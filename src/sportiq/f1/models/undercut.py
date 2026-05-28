"""Undercut window calculator — pure arithmetic.

undercut_window() determines how many laps it takes a faster-on-fresh-tyres
attacker to overcome the pit-lane time loss and clear the target car.
"""
from __future__ import annotations

import math


def undercut_window(
    driver_pace_s: float,
    target_pace_s: float,
    pit_loss_s: float,
    fresh_tyre_delta_s: float,
    gap_to_target_s: float,
) -> dict:
    """Compute the undercut window between an attacker and a target driver.

    Args:
        driver_pace_s: Attacker's current lap time in seconds.
        target_pace_s: Target driver's current lap time in seconds.
        pit_loss_s: Time lost in the pit lane (stationary + out-lap delta), seconds.
        fresh_tyre_delta_s: Lap-time advantage on fresh vs worn tyres, seconds.
                            Positive = fresher tyres are faster.
        gap_to_target_s: Current on-track gap from attacker to target, seconds.

    Returns:
        dict with keys:
            laps_to_clear (int | None): laps after the stop to overtake, None if never
            viable (bool): True if the undercut closes within 10 laps
            marginal (bool): True if viable but laps_to_clear > 5
    """
    if fresh_tyre_delta_s <= 0:
        return {"laps_to_clear": None, "viable": False, "marginal": False}

    # Net advantage per lap after the stop (target keeps current pace, attacker gains delta)
    net_gain_per_lap = fresh_tyre_delta_s - (driver_pace_s - target_pace_s)

    if net_gain_per_lap <= 0:
        return {"laps_to_clear": None, "viable": False, "marginal": False}

    # Total gap to overcome: current gap + pit-lane time loss
    total_gap = gap_to_target_s + pit_loss_s
    if total_gap <= 0:
        return {"laps_to_clear": 0, "viable": True, "marginal": False}

    laps = math.ceil(total_gap / net_gain_per_lap)
    viable = laps <= 10
    marginal = viable and laps > 5
    return {"laps_to_clear": laps, "viable": viable, "marginal": marginal}
