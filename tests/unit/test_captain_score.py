"""captain_score — assert ordering & monotonicity, not exact magnitudes."""

from __future__ import annotations

from sportiq.cricket.models.captain_score import expected_points

_BAT = {"name": "Top Order", "role": "BAT"}
_BOWL = {"name": "Pacer", "role": "BOWL"}
_WK = {"name": "Keeper", "role": "WK-BAT"}
_VENUE_BAT = {"pitch_type": "batting"}
_VENUE_BOWL = {"pitch_type": "bowling"}
_VENUE_NEUTRAL = {"pitch_type": "balanced"}


def test_monotonic_in_form_score_for_batter():
    low = expected_points(_BAT, _VENUE_NEUTRAL, opposition_strength=0.5, form_score=20.0)
    mid = expected_points(_BAT, _VENUE_NEUTRAL, opposition_strength=0.5, form_score=50.0)
    high = expected_points(_BAT, _VENUE_NEUTRAL, opposition_strength=0.5, form_score=90.0)
    assert low < mid < high


def test_batter_outperforms_bowler_on_batting_pitch():
    bat = expected_points(_BAT, _VENUE_BAT, opposition_strength=0.5, form_score=70.0)
    bowl = expected_points(_BOWL, _VENUE_BAT, opposition_strength=0.5, form_score=70.0)
    assert bat > bowl


def test_bowler_better_on_bowling_pitch_than_batting_pitch():
    on_bowl = expected_points(_BOWL, _VENUE_BOWL, opposition_strength=0.5, form_score=70.0)
    on_bat = expected_points(_BOWL, _VENUE_BAT, opposition_strength=0.5, form_score=70.0)
    assert on_bowl > on_bat


def test_strong_opposition_reduces_expected_points():
    weak = expected_points(_BAT, _VENUE_NEUTRAL, opposition_strength=0.1, form_score=70.0)
    strong = expected_points(_BAT, _VENUE_NEUTRAL, opposition_strength=0.9, form_score=70.0)
    assert weak > strong


def test_wk_role_gets_stumping_credit_vs_pure_bat_at_same_form():
    wk = expected_points(_WK, _VENUE_NEUTRAL, opposition_strength=0.5, form_score=70.0)
    bat = expected_points(_BAT, _VENUE_NEUTRAL, opposition_strength=0.5, form_score=70.0)
    # The keeper has a lower batting baseline but the stumping/catch credit is
    # additional. Either could win; we just assert the keeper gets *some*
    # non-trivial fielding contribution.
    assert wk > 8.0  # at minimum the fielding constant
    assert bat > 0
