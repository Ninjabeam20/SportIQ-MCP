"""Tests for the Poisson expected-goals match engine."""
from __future__ import annotations

from sportiq.football.models import poisson_xg


def test_outcome_probabilities_sum_to_one():
    probs = poisson_xg.outcome_probabilities(1.6, 1.1)
    assert abs(probs["home_win"] + probs["draw"] + probs["away_win"] - 1.0) < 1e-6


def test_stronger_side_favoured():
    # Big Elo edge -> home heavily favoured.
    lam_h, lam_a = poisson_xg.lambdas_from_elo(2100, 1600)
    probs = poisson_xg.outcome_probabilities(lam_h, lam_a)
    assert probs["home_win"] > probs["away_win"]
    assert probs["home_win"] > 0.5


def test_equal_sides_symmetric():
    lam_h, lam_a = poisson_xg.lambdas_from_elo(1800, 1800)
    assert abs(lam_h - lam_a) < 1e-9
    probs = poisson_xg.outcome_probabilities(lam_h, lam_a)
    assert abs(probs["home_win"] - probs["away_win"]) < 1e-6


def test_home_advantage_shifts_supremacy():
    neutral_h, _ = poisson_xg.lambdas_from_elo(1800, 1800, home_advantage=0.0)
    home_h, _ = poisson_xg.lambdas_from_elo(1800, 1800, home_advantage=60.0)
    assert home_h > neutral_h


def test_lambdas_never_negative():
    lam_h, lam_a = poisson_xg.lambdas_from_elo(1000, 2200)
    assert lam_h >= 0.05
    assert lam_a >= 0.05


def test_most_likely_scoreline_favours_stronger():
    lam_h, lam_a = poisson_xg.lambdas_from_elo(2100, 1500)
    gh, ga = poisson_xg.most_likely_scoreline(lam_h, lam_a)
    assert gh >= ga
