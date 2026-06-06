"""Group-stage Monte Carlo for the 2026 format (4-team round-robin).

Each group plays a full round-robin (6 matches). Match scores are sampled from
the Poisson engine; standings use 3/1/0 points with FIFA-style tiebreakers
(points -> goal difference -> goals for -> random). Returns finishing-position
probabilities, and exposes a single-draw helper the bracket sim composes across
all 12 groups (including the best-third ranking).
"""
from __future__ import annotations

import numpy as np

from sportiq.football.models.poisson_xg import lambdas_from_elo

# Within a group everyone is at a neutral venue, so no home advantage.
_NEUTRAL = 0.0


def _round_robin_pairs(teams: list[str]) -> list[tuple[int, int]]:
    return [(i, j) for i in range(len(teams)) for j in range(i + 1, len(teams))]


def simulate_group_once(
    rng: np.random.Generator,
    teams: list[str],
    ratings: dict[str, float],
) -> list[dict]:
    """Simulate one group's round-robin. Returns standings, best-to-worst.

    Each entry: ``{team, points, gd, gf, rank}`` where rank is 1..4. Ordering
    applies points -> goal difference -> goals for -> a random tiebreak.
    """
    points = dict.fromkeys(teams, 0)
    gf = dict.fromkeys(teams, 0)
    ga = dict.fromkeys(teams, 0)

    for i, j in _round_robin_pairs(teams):
        a, b = teams[i], teams[j]
        lam_a, lam_b = lambdas_from_elo(ratings.get(a, 1500.0), ratings.get(b, 1500.0), _NEUTRAL)
        goals_a = int(rng.poisson(lam_a))
        goals_b = int(rng.poisson(lam_b))
        gf[a] += goals_a
        gf[b] += goals_b
        ga[a] += goals_b
        ga[b] += goals_a
        if goals_a > goals_b:
            points[a] += 3
        elif goals_b > goals_a:
            points[b] += 3
        else:
            points[a] += 1
            points[b] += 1

    # Sort by (points, gd, gf, random) descending. The random key breaks exact ties.
    keyed = [
        (points[t], gf[t] - ga[t], gf[t], rng.random(), t)
        for t in teams
    ]
    keyed.sort(reverse=True)
    return [
        {"team": t, "points": p, "gd": gd, "gf": f, "rank": rank}
        for rank, (p, gd, f, _, t) in enumerate(keyed, start=1)
    ]


def simulate_group(
    teams: list[str],
    ratings: dict[str, float],
    n_iter: int = 10000,
    seed: int | None = None,
) -> dict:
    """Aggregate finishing-position probabilities for one group.

    Returns ``{team: {p_first, p_second, p_third, p_fourth, p_advance,
    avg_points}}`` plus ``iterations``. ``p_advance = p_first + p_second``.
    """
    if len(teams) != 4:
        raise ValueError(
            f"simulate_group expects exactly 4 teams (WC 2026 group format); got {len(teams)}."
        )
    rng = np.random.default_rng(seed)
    counts = {t: [0, 0, 0, 0] for t in teams}  # rank 1..4 tallies
    points_sum = dict.fromkeys(teams, 0)

    for _ in range(n_iter):
        standings = simulate_group_once(rng, teams, ratings)
        for row in standings:
            counts[row["team"]][row["rank"] - 1] += 1
            points_sum[row["team"]] += row["points"]

    out = {}
    for t in teams:
        c = counts[t]
        out[t] = {
            "p_first": round(c[0] / n_iter, 4),
            "p_second": round(c[1] / n_iter, 4),
            "p_third": round(c[2] / n_iter, 4),
            "p_fourth": round(c[3] / n_iter, 4),
            "p_advance": round((c[0] + c[1]) / n_iter, 4),
            "avg_points": round(points_sum[t] / n_iter, 2),
        }
    return {"teams": out, "iterations": n_iter}
