"""pitch_report model — single-record-in, summary-out."""

from __future__ import annotations

from sportiq.cricket.models.pitch_report import pitch_report


def test_batting_venue_is_high_friendly():
    record = {
        "name": "Wankhede Stadium",
        "city": "Mumbai",
        "pitch_type": "batting",
        "avg_first_innings": 178,
    }
    out = pitch_report(record)
    assert out["batting_friendly"] > 0.70
    assert out["expected_first_inn"] == 178
    assert "High-scoring" in out["recommendation"]


def test_bowling_venue_is_low_friendly():
    record = {
        "name": "M. A. Chidambaram Stadium",
        "city": "Chennai",
        "pitch_type": "bowling",
        "avg_first_innings": 158,
    }
    out = pitch_report(record)
    assert out["batting_friendly"] < 0.40
    assert "Bowler-friendly" in out["recommendation"]


def test_balanced_venue_lands_in_middle():
    record = {"name": "Eden Gardens", "pitch_type": "balanced", "avg_first_innings": 170}
    out = pitch_report(record)
    assert 0.40 <= out["batting_friendly"] <= 0.70


def test_missing_record_falls_back_to_balanced():
    out = pitch_report({})
    assert out["pitch_type"] == "balanced"
    assert out["expected_first_inn"] == 170
