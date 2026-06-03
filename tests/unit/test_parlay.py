"""Unit tests for sportiq.core.parlay.build_accumulator."""
from __future__ import annotations

from sportiq.core.parlay import build_accumulator


def _pick(event_id: str, outcome: str, edge: float, model_prob: float, market_odds: float, bookmaker: str = "betfair") -> dict:
    return {
        "event_id": event_id,
        "outcome": outcome,
        "edge": edge,
        "model_prob": model_prob,
        "market_odds": market_odds,
        "bookmaker": bookmaker,
    }


# -- basic functionality -------------------------------------------------------


def test_build_accumulator_basic():
    """5 picks, legs=3 → 3-leg acca with correct combined_odds."""
    picks = [
        _pick("m1", "home", 0.10, 0.55, 1.9),
        _pick("m2", "away", 0.08, 0.40, 2.5),
        _pick("m3", "home", 0.12, 0.60, 1.8),
        _pick("m4", "draw", 0.07, 0.35, 3.2),
        _pick("m5", "home", 0.06, 0.50, 2.1),
    ]
    result = build_accumulator(picks, legs=3, min_edge=0.05)

    assert result["legs_used"] == 3
    assert len(result["legs"]) == 3
    # Top 3 by edge: m3 (0.12), m1 (0.10), m2 (0.08)
    expected_odds = round(1.8 * 1.9 * 2.5, 4)
    assert abs(result["combined_odds"] - expected_odds) < 0.001


def test_deduplicates_same_match():
    """2 picks from same match_id → only 1 (highest edge) appears in legs."""
    picks = [
        _pick("m1", "home", 0.12, 0.60, 1.9),
        _pick("m1", "away", 0.07, 0.35, 3.0),  # same match, lower edge
    ]
    result = build_accumulator(picks, legs=3, min_edge=0.05)

    assert result["legs_used"] == 1
    # The higher-edge pick (home, 0.12) should be selected
    assert result["legs"][0]["outcome"] == "home"


def test_fewer_picks_than_legs():
    """2 picks, legs=5 → legs_used == 2 (no error)."""
    picks = [
        _pick("m1", "home", 0.10, 0.55, 2.0),
        _pick("m2", "away", 0.08, 0.45, 2.2),
    ]
    result = build_accumulator(picks, legs=5, min_edge=0.05)

    assert result["legs_used"] == 2
    assert len(result["legs"]) == 2
    assert "error" not in result


def test_min_edge_filter():
    """Picks with edge < min_edge are excluded."""
    picks = [
        _pick("m1", "home", 0.10, 0.55, 2.0),
        _pick("m2", "away", 0.03, 0.40, 2.5),  # edge below 0.05 threshold
        _pick("m3", "home", 0.04, 0.45, 2.3),  # edge below 0.05 threshold
    ]
    result = build_accumulator(picks, legs=3, min_edge=0.05)

    assert result["legs_used"] == 1
    assert result["legs"][0]["event_id"] == "m1"


def test_risk_flag_high_odds():
    """combined_odds > 10 → risk_flag == True."""
    picks = [
        _pick("m1", "home", 0.15, 0.60, 3.5),
        _pick("m2", "away", 0.12, 0.50, 2.0),
        _pick("m3", "home", 0.10, 0.55, 1.9),
    ]
    result = build_accumulator(picks, legs=3, min_edge=0.05)

    # combined_odds = 3.5 * 2.0 * 1.9 = 13.3 > 10
    assert result["combined_odds"] > 10
    assert result["risk_flag"] is True


def test_combined_edge_formula():
    """Manual verification of combined_edge = combined_model_prob - (1 / combined_odds)."""
    picks = [
        _pick("m1", "home", 0.10, 0.60, 2.0),
        _pick("m2", "away", 0.08, 0.50, 2.5),
    ]
    result = build_accumulator(picks, legs=2, min_edge=0.05)

    expected_combined_odds = 2.0 * 2.5  # 5.0
    expected_combined_prob = 0.60 * 0.50  # 0.30
    expected_edge = expected_combined_prob - (1.0 / expected_combined_odds)  # 0.30 - 0.20 = 0.10

    assert abs(result["combined_odds"] - expected_combined_odds) < 0.001
    assert abs(result["combined_model_prob"] - expected_combined_prob) < 0.001
    assert abs(result["combined_edge"] - expected_edge) < 0.001


def test_independence_warning_always_present():
    """independence_warning is always in the output, even for 0 picks."""
    # Zero picks case
    result_empty = build_accumulator([], legs=3, min_edge=0.05)
    assert "independence_warning" in result_empty
    assert "independence assumption" in result_empty["independence_warning"]

    # Non-empty picks case
    picks = [_pick("m1", "home", 0.10, 0.55, 2.0)]
    result_one = build_accumulator(picks, legs=3, min_edge=0.05)
    assert "independence_warning" in result_one
    assert "independence assumption" in result_one["independence_warning"]
