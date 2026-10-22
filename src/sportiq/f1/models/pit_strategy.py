"""F1 pit stop strategy predictor.

predict() sums the remaining-race time for staying out versus one stop
(at the best lap, on each legal next compound) and recommends the cheaper.
"""

from __future__ import annotations

from sportiq.f1.data.tyres import TYRE_SPECS, TyreCompound, normalize_compound
from sportiq.f1.models.tyre_deg import compound_key, fit_degradation

_DEFAULT_PIT_LOSS_S = 22.0  # seconds (typical pit-lane loss; circuits vary)


def _rainfall_mm(entry: dict) -> float:
    """Coerce OpenF1 rainfall to mm; None or non-numeric → dry (0.0)."""
    raw = entry.get("rainfall")
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


_DRY_COMPOUNDS = ("SOFT", "MEDIUM", "HARD")
# Decision-time rain: the share of the last _RAIN_WINDOW weather samples with
# rainfall must reach _RAIN_SHARE. One wet sample anywhere no longer flips to INTER.
_RAIN_WINDOW = 10
_RAIN_SHARE = 0.5


def _stint_total(base: float, slope: float, first_age: int, laps: int) -> float:
    """Sum of (base + slope * a) for tyre ages a = first_age .. first_age+laps-1."""
    if laps <= 0:
        return 0.0
    age_sum = laps * first_age + laps * (laps - 1) / 2
    return laps * base + slope * age_sum


def _current_stint(stints: list[dict], current_lap: int) -> dict | None:
    """The stint running at ``current_lap`` (latest one started by then), else the latest."""
    started = [s for s in stints if (s.get("lap_start") or 0) <= current_lap]
    pool = started or stints
    return max(pool, key=lambda s: s.get("lap_start") or 0) if pool else None


def predict(
    laps: list[dict],
    stints: list[dict],
    weather: list[dict],
    current_lap: int,
    total_laps: int,
    pit_loss_s: float = _DEFAULT_PIT_LOSS_S,
) -> dict:
    """Predict optimal pit stop strategy for the remainder of the race.

    Compares the remaining-race time of staying out on the current tyre
    (``sum(base_c + slope_c * (age_now + k))``, k = 1..R) with stopping once
    (``pit_loss + old-tyre laps + sum(base_n + slope_n * (k - 1))`` on each legal
    next compound), over every stop lap, and recommends the stop when its
    total is lower. ``base``/``slope`` come from the per-compound fit, else
    the ``TYRE_SPECS`` delta/rate anchored on the fitted compound.

    Args:
        laps: Lap dicts from OpenF1 /laps (lap_duration, compound, tyre_life).
        stints: Stint dicts from OpenF1 /stints (compound, lap_start, lap_end,
            tyre_age_at_start).
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
            net_saving_s (float): stay-out total - best one-stop total (negative
                when a stop is only taken to satisfy the two-dry-compound rule)
            current_tyre_age (int): laps on the current set at ``current_lap``
    """
    # Determine current compound and tyre age from the stint running now.
    current_compound = "MEDIUM"
    current_tyre_age = 0
    stint = _current_stint(stints, current_lap)
    if stint is not None:
        # "INTERMEDIATE" (OpenF1) → INTER; missing or unknown → MEDIUM.
        current_compound = str(normalize_compound(stint.get("compound")) or "MEDIUM")
        age_at_start = stint.get("tyre_age_at_start") or 0
        current_tyre_age = int(age_at_start) + max(
            0, current_lap - (stint.get("lap_start") or current_lap)
        )

    remaining = total_laps - current_lap
    if remaining <= 0:
        return {
            "stop_laps": [],
            "compound_sequence": [],
            "expected_finish_position": None,
            "confidence": 0.0,
            "net_saving_s": 0.0,
            "current_tyre_age": current_tyre_age,
        }

    # Fit degradation per compound from available laps
    compounds = list({compound_key(lap.get("compound")) for lap in laps if lap.get("compound")})
    deg_models: dict[str, dict] = {}
    for c in compounds:
        model = fit_degradation(laps, c)
        if model["sample_count"] >= 2:
            deg_models[c] = model

    recent = weather[-_RAIN_WINDOW:]
    has_rain = bool(recent) and (
        sum(_rainfall_mm(w) > 0 for w in recent) / len(recent) >= _RAIN_SHARE
    )

    try:
        compound_enum = TyreCompound(current_compound)
    except ValueError:
        compound_enum = TyreCompound.MEDIUM
        current_compound = "MEDIUM"
    deg_model = deg_models.get(current_compound, {})
    confidence = min(1.0, deg_model.get("sample_count", 0) / 20.0)

    if has_rain:
        # Rain: stop as soon as possible for intermediates
        return {
            "stop_laps": [current_lap + 1],
            "compound_sequence": [current_compound, "INTER"],
            "expected_finish_position": None,
            "confidence": round(max(0.5, confidence), 3),
            "net_saving_s": 0.0,
            "current_tyre_age": current_tyre_age,
        }

    # Absolute lap-time anchor: a fitted intercept minus its spec delta, so an
    # unfitted compound's base sits on the same scale (a common constant
    # cancels between options anyway, which is why 0.0 is a safe fallback).
    fitted_known = [c for c in deg_models if normalize_compound(c) is not None]
    anchor_compound = current_compound if current_compound in deg_models else None
    if anchor_compound is None and fitted_known:
        anchor_compound = sorted(fitted_known)[0]
    anchor = 0.0
    if anchor_compound is not None:
        anchor = (
            deg_models[anchor_compound]["intercept"]
            - TYRE_SPECS[TyreCompound(anchor_compound)].base_lap_delta_s
        )

    def _params(compound: str) -> tuple[float, float]:
        spec = TYRE_SPECS[TyreCompound(compound)]
        fit = deg_models.get(compound)
        if fit is not None:
            return fit["intercept"], fit["slope"]
        return anchor + spec.base_lap_delta_s, spec.degradation_rate_s_per_lap

    base_c, slope_c = _params(compound_enum.value)
    stay_total = _stint_total(base_c, slope_c, current_tyre_age + 1, remaining)

    # Legal next compounds. A dry race must use >= 2 dry compounds: when the
    # only dry compound used so far is the current one, it can't be the next.
    used_dry = {
        str(normalize_compound(s.get("compound")))
        for s in stints
        if (s.get("lap_start") or 0) <= current_lap
        and str(normalize_compound(s.get("compound"))) in _DRY_COMPOUNDS
    }
    needs_second_dry = current_compound in _DRY_COMPOUNDS and used_dry <= {current_compound}
    candidates = [c for c in _DRY_COMPOUNDS if not (needs_second_dry and c == current_compound)]

    # Best single stop: stay j more laps on the old set (j = 0 is "pit at the
    # next lap"), then R - j laps on a fresh set of compound n.
    best: tuple[float, int, str] | None = None
    for n in candidates:
        base_n, slope_n = _params(n)
        for j in range(remaining):
            total = (
                pit_loss_s
                + _stint_total(base_c, slope_c, current_tyre_age + 1, j)
                + _stint_total(base_n, slope_n, 0, remaining - j)
            )
            if best is None or total < best[0]:
                best = (total, j, n)

    assert best is not None  # remaining > 0 and candidates is never empty
    best_total, best_j, best_n = best
    net_saving = stay_total - best_total

    if net_saving > 0 or needs_second_dry:
        stop_laps = [current_lap + best_j + 1]
        compound_sequence = [current_compound, best_n]
    else:
        stop_laps = []
        compound_sequence = [current_compound]

    return {
        "stop_laps": stop_laps,
        "compound_sequence": compound_sequence,
        "expected_finish_position": None,
        "confidence": round(confidence, 3),
        "net_saving_s": round(net_saving, 2),
        "current_tyre_age": current_tyre_age,
    }
