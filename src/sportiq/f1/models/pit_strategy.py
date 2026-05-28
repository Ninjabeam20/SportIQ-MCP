"""F1 pit stop strategy predictor.

predict() walks a synthetic race lap-by-lap, choosing stops where
projected lap-time savings exceed pit-lane loss.
"""
from __future__ import annotations

from sportiq.f1.data.tyres import TYRE_SPECS, TyreCompound
from sportiq.f1.models.tyre_deg import fit_degradation

_DEFAULT_PIT_LOSS_S = 22.0  # seconds (typical pit-lane loss; circuits vary)


def predict(
    laps: list[dict],
    stints: list[dict],
    weather: list[dict],
    current_lap: int,
    total_laps: int,
    pit_loss_s: float = _DEFAULT_PIT_LOSS_S,
) -> dict:
    """Predict optimal pit stop strategy for the remainder of the race.

    Args:
        laps: Lap dicts from OpenF1 /laps (lap_duration, compound, tyre_life).
        stints: Stint dicts from OpenF1 /stints (compound, lap_start, lap_end).
        weather: Weather dicts from OpenF1 /weather (rainfall, track_temperature).
        current_lap: Current lap number.
        total_laps: Total race laps.
        pit_loss_s: Pit-lane time loss in seconds.

    Returns:
        dict with keys:
            stop_laps (list[int]): recommended pit lap numbers
            compound_sequence (list[str]): compound for each stint
            expected_finish_position (int | None): None — not modelled in Phase 3
            confidence (float): 0.0-1.0 based on sample count quality
    """
    remaining = total_laps - current_lap
    if remaining <= 0:
        return {
            "stop_laps": [],
            "compound_sequence": [],
            "expected_finish_position": None,
            "confidence": 0.0,
        }

    # Determine current compound from most recent stint
    current_compound = "MEDIUM"
    if stints:
        latest = max(stints, key=lambda s: s.get("lap_start", 0))
        current_compound = latest.get("compound", "MEDIUM").upper()

    # Fit degradation per compound from available laps
    compounds = list({lap.get("compound", "").upper() for lap in laps if lap.get("compound")})
    deg_models: dict[str, dict] = {}
    for c in compounds:
        model = fit_degradation(laps, c)
        if model["sample_count"] >= 2:
            deg_models[c] = model

    # Check rainfall — if any rain recorded, recommend intermediates
    has_rain = any(float(w.get("rainfall", 0)) > 0 for w in weather)

    # Simple 1-stop or 2-stop decision based on remaining laps + degradation slope
    current_spec = TYRE_SPECS.get(TyreCompound(current_compound), TYRE_SPECS[TyreCompound.MEDIUM])
    deg_model = deg_models.get(current_compound, {"slope": current_spec.degradation_rate_s_per_lap})
    slope = deg_model.get("slope", current_spec.degradation_rate_s_per_lap)

    # Projected total time loss on current compound vs a fresh switch.
    # Two triggers for a pit stop:
    #   1. Cumulative degradation (slope * remaining) exceeds pit-lane loss — classic break-even.
    #   2. Remaining laps exceed the compound's safe window — tyre will fall off a cliff.
    projected_loss = slope * remaining

    stop_laps: list[int] = []
    compound_sequence: list[str] = [current_compound]
    confidence = min(1.0, (deg_model.get("sample_count", 0) if "sample_count" in deg_model else 0) / 20.0)

    stop_warranted = (
        projected_loss > pit_loss_s
        or remaining > current_spec.safe_window_laps
    )

    if has_rain:
        # Rain: stop as soon as possible for intermediates
        stop_laps = [current_lap + 1]
        compound_sequence = [current_compound, "INTER"]
        confidence = max(0.5, confidence)
    elif stop_warranted and remaining > 10:
        # One stop is beneficial
        # Choose stop point at ~40% remaining distance (typical 1-stop strategy)
        stop_lap = current_lap + max(5, int(remaining * 0.4))
        stop_laps = [stop_lap]

        # Pick next compound: if current is SOFT → MEDIUM/HARD, else → HARD
        if current_compound == "SOFT":
            next_compound = "MEDIUM" if remaining > 25 else "HARD"
        elif current_compound == "MEDIUM":
            next_compound = "HARD"
        else:
            next_compound = "MEDIUM"

        compound_sequence = [current_compound, next_compound]

        # Consider 2-stop if remaining laps is large
        if remaining > 35 and slope > 0.07:
            stop2 = stop_lap + max(5, int(remaining * 0.35))
            if stop2 < total_laps - 5:
                stop_laps.append(stop2)
                compound_sequence.append("SOFT")
    # else: no stop — stay out

    return {
        "stop_laps": stop_laps,
        "compound_sequence": compound_sequence,
        "expected_finish_position": None,
        "confidence": round(confidence, 3),
    }
