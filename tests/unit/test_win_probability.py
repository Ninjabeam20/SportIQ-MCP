"""Unit tests for the cricket T20 win probability model."""
import random

from sportiq.cricket.models.win_probability import win_prob


def test_equal_signals_gives_near_50_50():
    result = win_prob({}, {})
    assert abs(result["team_a"] - 0.5) < 0.01
    assert abs(result["team_b"] - 0.5) < 0.01
    assert abs(result["team_a"] + result["team_b"] - 1.0) < 0.001


def test_better_form_wins():
    a = {"form_score": 80, "h2h_win_rate": 0.6}
    b = {"form_score": 40, "h2h_win_rate": 0.4}
    result = win_prob(a, b)
    assert result["team_a"] > result["team_b"]


def test_probs_sum_to_one():
    for _ in range(20):
        a = {"form_score": random.uniform(0, 100), "h2h_win_rate": random.uniform(0, 1)}
        b = {"form_score": random.uniform(0, 100), "h2h_win_rate": random.uniform(0, 1)}
        result = win_prob(a, b)
        assert abs(result["team_a"] + result["team_b"] - 1.0) < 1e-9


def test_venue_tilt_applies():
    a = {"venue_tilt": 0.8}
    b = {"venue_tilt": 0.2}
    result = win_prob(a, b)
    assert result["team_a"] > 0.5


def test_returns_dict_with_expected_keys():
    result = win_prob({}, {})
    assert set(result.keys()) == {"team_a", "team_b"}


def test_extreme_form_dominates():
    """A team with near-perfect form + H2H should win convincingly."""
    a = {"form_score": 100, "h2h_win_rate": 1.0}
    b = {"form_score": 0, "h2h_win_rate": 0.0}
    result = win_prob(a, b)
    assert result["team_a"] >= 0.9
    assert result["team_a"] > result["team_b"]


def test_h2h_signal_not_double_flipped():
    """h2h_win_rate=0.6 for team_a and 0.4 for team_b should favour team_a.

    Regression for the bug where b_h2h was computed as 1.0-b_rate instead
    of b_rate directly, causing both teams to get the same h2h advantage.
    """
    a = {"h2h_win_rate": 0.6}
    b = {"h2h_win_rate": 0.4}
    result = win_prob(a, b)
    assert result["team_a"] > result["team_b"], (
        "team_a with 60% H2H win rate should beat team_b with 40%"
    )


def test_core_value_bet_reexport():
    """football/models/value_bet still works after re-exporting from core."""
    from sportiq.football.models.value_bet import devig, find_value, implied_prob

    assert implied_prob(2.0) == 0.5
    assert devig({"home": 0.6, "away": 0.5}) == {"home": 0.6 / 1.1, "away": 0.5 / 1.1}
    bk = {"name": "bet365", "home": 1.8, "away": 2.2, "draw": None}
    picks = find_value({"home_win": 0.7, "away_win": 0.3}, bk, min_edge=0.05)
    assert all("edge" in p for p in picks)
