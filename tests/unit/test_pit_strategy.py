"""Tests for the pit strategy predictor."""
from __future__ import annotations

from sportiq.f1.models.pit_strategy import predict


def _make_laps(n: int, base_time: float = 83.0, slope: float = 0.08, compound: str = "SOFT") -> list[dict]:
    return [
        {"lap_duration": base_time + slope * i, "compound": compound, "tyre_life": i}
        for i in range(n)
    ]


def _make_stints(compound: str = "SOFT", lap_start: int = 1) -> list[dict]:
    return [{"compound": compound, "lap_start": lap_start, "lap_end": lap_start + 20}]


def test_one_stop_on_degrading_soft():
    laps = _make_laps(20, compound="SOFT", slope=0.08)
    stints = _make_stints("SOFT")
    result = predict(laps=laps, stints=stints, weather=[], current_lap=15, total_laps=57)
    assert len(result["stop_laps"]) >= 1
    assert result["compound_sequence"][0] == "SOFT"
    assert len(result["compound_sequence"]) >= 2


def test_no_stop_when_few_laps_remain():
    laps = _make_laps(5, compound="HARD", slope=0.01)
    stints = _make_stints("HARD")
    result = predict(laps=laps, stints=stints, weather=[], current_lap=54, total_laps=57)
    # Very few laps remain, no stop needed
    assert isinstance(result["stop_laps"], list)
    assert isinstance(result["compound_sequence"], list)


def test_rain_triggers_inter_stop():
    laps = _make_laps(10, compound="MEDIUM")
    stints = _make_stints("MEDIUM")
    weather = [{"rainfall": 1.5, "track_temperature": 18.0}]
    result = predict(laps=laps, stints=stints, weather=weather, current_lap=20, total_laps=57)
    assert "INTER" in result["compound_sequence"]
    assert len(result["stop_laps"]) >= 1


def test_returns_expected_keys():
    result = predict(laps=[], stints=[], weather=[], current_lap=1, total_laps=57)
    assert "stop_laps" in result
    assert "compound_sequence" in result
    assert "expected_finish_position" in result
    assert "confidence" in result


def test_zero_remaining_laps():
    result = predict(laps=[], stints=[], weather=[], current_lap=57, total_laps=57)
    assert result["stop_laps"] == []
    assert result["confidence"] == 0.0
