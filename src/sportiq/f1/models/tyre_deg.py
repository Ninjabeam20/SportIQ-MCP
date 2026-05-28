"""Tyre degradation linear model.

fit_degradation() fits a linear model (lap_time = intercept + slope * lap_on_tyre)
to a list of lap dicts, returning the model parameters.
"""
from __future__ import annotations

import numpy as np


def fit_degradation(laps: list[dict], compound: str) -> dict:
    """Fit a linear tyre degradation model for one compound.

    Filters laps to the given compound, removes in/out laps and SC laps
    (heuristic: lap_duration > mean + 2*std treated as outlier/SC lap),
    then fits degree-1 polyfit over tyre_age (or lap order if tyre_age absent).

    Args:
        laps: List of lap dicts. Each should have:
            - ``lap_duration`` (float, seconds) — None or 0 treated as invalid
            - ``compound`` (str) — tyre compound name
            - ``tyre_life`` (int, optional) — laps on this tyre set
        compound: Compound to filter to (e.g. "SOFT", "MEDIUM", "HARD").

    Returns:
        dict with keys:
            intercept (float): fitted intercept in seconds
            slope (float): seconds degradation per lap
            residual_std (float): std of residuals (model quality indicator)
            sample_count (int): number of valid laps used in the fit
    """
    valid = [
        lap for lap in laps
        if lap.get("compound", "").upper() == compound.upper()
        and lap.get("lap_duration") is not None
        and float(lap["lap_duration"]) > 0
    ]

    if len(valid) < 2:
        return {"intercept": 0.0, "slope": 0.0, "residual_std": 0.0, "sample_count": len(valid)}

    durations = np.array([float(lap["lap_duration"]) for lap in valid])

    # Remove outliers (SC laps, in/out laps): drop anything > mean + 2*std
    mean, std = durations.mean(), durations.std()
    if std > 0:
        mask = durations <= mean + 2 * std
        valid = [lap for lap, keep in zip(valid, mask, strict=True) if keep]
        durations = durations[mask]

    if len(valid) < 2:
        return {"intercept": float(durations[0]), "slope": 0.0, "residual_std": 0.0, "sample_count": 1}

    # Tyre age axis: use tyre_life if present, else lap index
    tyre_ages = np.array([
        float(lap.get("tyre_life", i))
        for i, lap in enumerate(valid)
    ])

    coeffs = np.polyfit(tyre_ages, durations, deg=1)
    fitted = np.polyval(coeffs, tyre_ages)
    residuals = durations - fitted

    return {
        "intercept": float(coeffs[1]),
        "slope": float(coeffs[0]),
        "residual_std": float(residuals.std()),
        "sample_count": len(valid),
    }
