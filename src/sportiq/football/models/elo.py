"""Elo rating helpers for football.

Pure functions, no I/O. Seed ratings are loaded by the adapters from
``elo_seed.json``; these functions take ratings as plain floats so the models
and tests stay deterministic.
"""
from __future__ import annotations

_HOME_ADVANTAGE_ELO = 60.0  # Elo points added to the home/seeded side


def expected_score(rating_a: float, rating_b: float, home_advantage: float = 0.0) -> float:
    """Elo win-expectation for A vs B (draws count as half), in [0, 1].

    Args:
        rating_a: Elo rating of side A.
        rating_b: Elo rating of side B.
        home_advantage: Elo points to add to A (0 for a neutral venue).
    """
    return 1.0 / (1.0 + 10.0 ** (-((rating_a + home_advantage) - rating_b) / 400.0))


def update_rating(rating: float, expected: float, actual: float, k: float = 30.0) -> float:
    """Return the post-match Elo rating.

    Args:
        rating: Current rating.
        expected: Expected score from ``expected_score`` (0..1).
        actual: Actual result for this side: 1.0 win, 0.5 draw, 0.0 loss.
        k: K-factor (sensitivity). 30 is a reasonable international default.
    """
    return rating + k * (actual - expected)
