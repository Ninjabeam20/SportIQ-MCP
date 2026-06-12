"""Poisson expected-goals match engine.

Two teams' expected goals (lambda_home, lambda_away) -> a scoreline probability
matrix via ``scipy.stats.poisson`` -> P(home win / draw / away win). The same
engine drives the standalone xG tool and the group/bracket Monte Carlo sims.

Expected goals are derived from Elo (the seed we always have) or, when team
attack/defense rates are available, from those directly.
"""
from __future__ import annotations

import numpy as np

# scipy is the heaviest import in the tree (~0.4s) and is only needed inside
# scoreline_matrix(). Deferred to the function body so it stays off the Cloud Run
# cold-start path — boot only pays for it when a Poisson tool actually runs.

# Tournament-match tuning. WC group games average ~2.6 total goals; each 100 Elo
# of edge is worth ~0.4 goals of supremacy (calibrated to be sane, not exact).
_AVG_TOTAL_GOALS = 2.6
_SUPREMACY_PER_ELO = 0.004
_MIN_LAMBDA = 0.05
_MAX_GOALS = 10  # truncate the scoreline grid; >10 goals is negligible mass


def lambdas_from_elo(
    elo_home: float,
    elo_away: float,
    home_advantage: float = 0.0,
    avg_total_goals: float = _AVG_TOTAL_GOALS,
) -> tuple[float, float]:
    """Map an Elo matchup onto (expected_home_goals, expected_away_goals).

    Args:
        elo_home: Elo of the home/first side.
        elo_away: Elo of the away/second side.
        home_advantage: Elo points to add to the home side (0 at a neutral venue).
        avg_total_goals: Expected combined goals for an even match.
    """
    supremacy = ((elo_home + home_advantage) - elo_away) * _SUPREMACY_PER_ELO
    lambda_home = max(_MIN_LAMBDA, (avg_total_goals + supremacy) / 2.0)
    lambda_away = max(_MIN_LAMBDA, (avg_total_goals - supremacy) / 2.0)
    return lambda_home, lambda_away


def lambdas_from_strength(
    attack_home: float,
    defense_away: float,
    attack_away: float,
    defense_home: float,
    league_avg_goals: float = 1.3,
) -> tuple[float, float]:
    """Expected goals from attack/defense strength ratios (Dixon-Coles style).

    Strengths are multipliers around 1.0 (1.0 = league average). Used when real
    per-team scoring rates are available instead of only Elo.
    """
    lambda_home = max(_MIN_LAMBDA, attack_home * defense_away * league_avg_goals)
    lambda_away = max(_MIN_LAMBDA, attack_away * defense_home * league_avg_goals)
    return lambda_home, lambda_away


def scoreline_matrix(lambda_home: float, lambda_away: float, max_goals: int = _MAX_GOALS) -> np.ndarray:
    """Return the (max_goals+1, max_goals+1) joint scoreline probability grid.

    ``matrix[i, j]`` is P(home scores i, away scores j), assuming independent
    Poisson goal counts.
    """
    from scipy.stats import poisson

    goals = np.arange(max_goals + 1)
    home_pmf = poisson.pmf(goals, lambda_home)
    away_pmf = poisson.pmf(goals, lambda_away)
    return np.outer(home_pmf, away_pmf)


def outcome_probabilities(lambda_home: float, lambda_away: float) -> dict:
    """Return {home_win, draw, away_win} from the scoreline matrix (sums to ~1)."""
    matrix = scoreline_matrix(lambda_home, lambda_away)
    home_win = float(np.tril(matrix, -1).sum())  # i > j
    away_win = float(np.triu(matrix, 1).sum())   # i < j
    draw = float(np.trace(matrix))               # i == j
    total = home_win + draw + away_win
    return {
        "home_win": round(home_win / total, 4),
        "draw": round(draw / total, 4),
        "away_win": round(away_win / total, 4),
    }


def most_likely_scoreline(lambda_home: float, lambda_away: float) -> tuple[int, int]:
    """Return the single most probable (home_goals, away_goals) scoreline."""
    matrix = scoreline_matrix(lambda_home, lambda_away)
    i, j = np.unravel_index(int(np.argmax(matrix)), matrix.shape)
    return int(i), int(j)
