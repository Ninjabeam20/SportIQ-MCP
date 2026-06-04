"""Race pace comparison model.

compare_race_pace() fits a per-compound degradation model for two drivers and
computes the pace delta (intercept difference) on each shared compound.
"""
from __future__ import annotations

from sportiq.f1.models.tyre_deg import annotate_laps_with_stints, fit_degradation


def compare_race_pace(
    laps_a: list[dict],
    stints_a: list[dict],
    laps_b: list[dict],
    stints_b: list[dict],
    driver_a: int,
    driver_b: int,
) -> dict:
    """Compare race pace and tyre degradation between two drivers by compound.

    For each compound present in both drivers' data, fits a linear degradation
    model (intercept + slope * tyre_age) and computes the fresh-tyre pace delta.

    Args:
        laps_a: Lap dicts for driver_a.
        stints_a: Stint dicts for driver_a (used for compound/tyre_life annotation).
        laps_b: Lap dicts for driver_b.
        stints_b: Stint dicts for driver_b.
        driver_a: Race number for first driver.
        driver_b: Race number for second driver.

    Returns:
        dict with keys driver_a, driver_b, by_compound, overall_faster,
        compounds_compared.
    """
    annotated_a = annotate_laps_with_stints(laps_a, stints_a)
    annotated_b = annotate_laps_with_stints(laps_b, stints_b)

    # Collect distinct compounds for each driver
    compounds_a = {
        lap["compound"].upper()
        for lap in annotated_a
        if lap.get("compound") and lap.get("lap_duration") and float(lap["lap_duration"]) > 0
    }
    compounds_b = {
        lap["compound"].upper()
        for lap in annotated_b
        if lap.get("compound") and lap.get("lap_duration") and float(lap["lap_duration"]) > 0
    }

    shared = compounds_a & compounds_b
    by_compound: list[dict] = []

    wins_a = 0
    wins_b = 0

    for compound in sorted(shared):
        fit_a = fit_degradation(annotated_a, compound)
        fit_b = fit_degradation(annotated_b, compound)

        # Skip if either driver has insufficient data
        if fit_a["sample_count"] == 0 or fit_b["sample_count"] == 0:
            continue

        pace_delta = fit_a["intercept"] - fit_b["intercept"]
        faster = driver_a if pace_delta < 0 else driver_b

        if pace_delta < 0:
            wins_a += 1
        elif pace_delta > 0:
            wins_b += 1
        # exact tie: neither gets a win

        by_compound.append(
            {
                "compound": compound,
                "intercept_a": fit_a["intercept"],
                "intercept_b": fit_b["intercept"],
                "slope_a": fit_a["slope"],
                "slope_b": fit_b["slope"],
                "pace_delta_s": pace_delta,
                "faster_driver": faster,
                "sample_count_a": fit_a["sample_count"],
                "sample_count_b": fit_b["sample_count"],
            }
        )

    if wins_a > wins_b:
        overall_faster: int | None = driver_a
    elif wins_b > wins_a:
        overall_faster = driver_b
    else:
        overall_faster = None

    return {
        "driver_a": driver_a,
        "driver_b": driver_b,
        "by_compound": by_compound,
        "overall_faster": overall_faster,
        "compounds_compared": len(by_compound),
    }
