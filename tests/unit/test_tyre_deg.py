"""Tests for tyre degradation model."""
from __future__ import annotations

from sportiq.f1.models.tyre_deg import annotate_laps_with_stints, fit_degradation


def _make_laps(times: list[float], compound: str = "SOFT") -> list[dict]:
    return [
        {"lap_duration": t, "compound": compound, "tyre_life": i}
        for i, t in enumerate(times)
    ]


def test_positive_slope_increasing_lap_times():
    # Lap times increasing → positive slope (degradation)
    laps = _make_laps([80.0, 80.08, 80.16, 80.24, 80.32, 80.40], compound="SOFT")
    result = fit_degradation(laps, "SOFT")
    assert result["slope"] > 0
    assert result["sample_count"] == 6


def test_flat_data_near_zero_slope():
    laps = _make_laps([80.0, 80.0, 80.0, 80.0, 80.0], compound="MEDIUM")
    result = fit_degradation(laps, "MEDIUM")
    assert abs(result["slope"]) < 0.01


def test_outlier_filtered():
    # One safety car lap (very slow) should be filtered
    laps = _make_laps([80.0, 80.1, 80.2, 120.0, 80.3, 80.4], compound="HARD")
    result = fit_degradation(laps, "HARD")
    assert result["sample_count"] < 6  # 120.0 outlier removed


def test_wrong_compound_returns_empty():
    laps = _make_laps([80.0, 80.1], compound="SOFT")
    result = fit_degradation(laps, "MEDIUM")
    assert result["sample_count"] == 0
    assert result["slope"] == 0.0


def test_single_lap_returns_no_slope():
    laps = _make_laps([80.0], compound="SOFT")
    result = fit_degradation(laps, "SOFT")
    assert result["slope"] == 0.0


# -- annotate_laps_with_stints (OpenF1 /laps + /stints merge) ------------------


def test_annotate_adds_compound_and_tyre_life_from_stint():
    # Real OpenF1 /laps carry neither compound nor tyre_life.
    laps = [{"lap_number": n, "lap_duration": 80.0} for n in range(1, 6)]
    stints = [{"lap_start": 1, "lap_end": 5, "compound": "SOFT", "tyre_age_at_start": 3}]
    annotated = annotate_laps_with_stints(laps, stints)
    assert all(lap["compound"] == "SOFT" for lap in annotated)
    # tyre_life = tyre_age_at_start + (lap_number - lap_start): 3,4,5,6,7
    assert [lap["tyre_life"] for lap in annotated] == [3, 4, 5, 6, 7]


def test_annotate_leaves_uncovered_laps_unchanged():
    laps = [{"lap_number": 99, "lap_duration": 80.0}]
    stints = [{"lap_start": 1, "lap_end": 5, "compound": "SOFT", "tyre_age_at_start": 0}]
    annotated = annotate_laps_with_stints(laps, stints)
    assert "compound" not in annotated[0]
    assert "tyre_life" not in annotated[0]


def test_fit_on_real_shape_laps_yields_positive_slope():
    # The audit's regression check (#1): laps without compound, merged from a
    # degrading stint, must produce a non-zero positive slope — proving the
    # model now consumes telemetry instead of falling back to constants.
    laps = [
        {"lap_number": n, "lap_duration": round(80.0 + 0.09 * (n - 1), 3)}
        for n in range(1, 16)
    ]
    stints = [{"lap_start": 1, "lap_end": 15, "compound": "SOFT", "tyre_age_at_start": 0}]
    annotated = annotate_laps_with_stints(laps, stints)
    result = fit_degradation(annotated, "SOFT")
    assert result["slope"] > 0
    assert result["sample_count"] >= 2
