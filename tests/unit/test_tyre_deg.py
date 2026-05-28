"""Tests for tyre degradation model."""
from __future__ import annotations

from sportiq.f1.models.tyre_deg import fit_degradation


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
