"""Full-tournament Monte Carlo for WC 2026 (48 teams, 12 groups, R32 knockout).

Per iteration: simulate all 12 groups, take the top 2 of each plus the 8 best
third-placed teams (32 qualifiers), strength-seed them into a single-elimination
bracket, and play it to a champion. Aggregating over many iterations yields each
team's probability of reaching every round and of winning the tournament.

Bracket seeding note: the official 2026 third-place allocation table is not used.
Qualifiers are strength-seeded (group points -> GD -> GF) into a standard
1-vs-N bracket. This keeps strong teams apart until late rounds (realistic) and
is fully deterministic under a fixed seed; matching FIFA's exact slotting is a
documented follow-up. The convergence and slot-sum invariants hold regardless.
"""
from __future__ import annotations

import numpy as np

from sportiq.football.models.elo import expected_score
from sportiq.football.models.group_sim import simulate_group_once
from sportiq.football.models.poisson_xg import lambdas_from_elo

_STAGES = ["R32", "R16", "QF", "SF", "Final", "Winner"]
# Round labels for the 5 knockout reductions starting from 32 qualifiers.
_KO_ROUNDS = ["R16", "QF", "SF", "Final", "Winner"]


def _seed_order(n: int) -> list[int]:
    """Standard single-elimination seeding positions for ``n`` (power of two).

    Returns the seed numbers (1-based) in bracket order, so that top seeds only
    meet in the final (e.g. n=4 -> [1, 4, 3, 2]).
    """
    order = [1]
    while len(order) < n:
        m = len(order) * 2
        order = [x for s in order for x in (s, m + 1 - s)]
    return order


def _knockout_winner(
    rng: np.random.Generator,
    team_a: str,
    team_b: str,
    ratings: dict[str, float],
) -> str:
    """Decide one knockout tie. Draws after normal time go to a weighted shootout."""
    ra, rb = ratings.get(team_a, 1500.0), ratings.get(team_b, 1500.0)
    lam_a, lam_b = lambdas_from_elo(ra, rb, 0.0)
    goals_a = int(rng.poisson(lam_a))
    goals_b = int(rng.poisson(lam_b))
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    return team_a if rng.random() < expected_score(ra, rb) else team_b


def _simulate_once(
    rng: np.random.Generator,
    groups: dict[str, list[str]],
    ratings: dict[str, float],
) -> dict[str, int]:
    """One tournament. Returns ``{team: furthest_stage_index}`` for qualifiers."""
    winners, runners, thirds = [], [], []
    for teams in groups.values():
        standings = simulate_group_once(rng, teams, ratings)
        winners.append(standings[0])
        runners.append(standings[1])
        thirds.append(standings[2])

    best_thirds = sorted(
        thirds, key=lambda r: (r["points"], r["gd"], r["gf"], rng.random()), reverse=True
    )[:8]
    qualifiers = winners + runners + best_thirds  # 32

    reached: dict[str, int] = {q["team"]: 0 for q in qualifiers}  # 0 == reached R32

    seeded = sorted(
        qualifiers, key=lambda r: (r["points"], r["gd"], r["gf"], rng.random()), reverse=True
    )
    seed_team = {s: seeded[s - 1]["team"] for s in range(1, len(seeded) + 1)}
    current = [seed_team[s] for s in _seed_order(len(seeded))]

    for stage_idx, _round in enumerate(_KO_ROUNDS, start=1):
        nxt = []
        for k in range(0, len(current), 2):
            winner = _knockout_winner(rng, current[k], current[k + 1], ratings)
            reached[winner] = stage_idx
            nxt.append(winner)
        current = nxt
    return reached


def simulate_tournament(
    groups: dict[str, list[str]],
    ratings: dict[str, float],
    n_iter: int = 10000,
    seed: int | None = None,
) -> dict:
    """Monte Carlo the whole tournament. Returns per-team round probabilities.

    Args:
        groups: ``{group_letter: [4 team codes]}`` — the full 12-group draw.
        ratings: ``{team_code: elo}`` for every team in ``groups``.
        n_iter: iterations (10k gives stable ±2% probabilities).
        seed: RNG seed for reproducibility.

    Returns:
        ``{"teams": {code: {reach_r32, reach_r16, reach_qf, reach_sf,
        reach_final, win}}, "iterations": n, "champion": code}`` — teams sorted
        by win probability (descending).
    """
    rng = np.random.default_rng(seed)
    all_teams = [t for teams in groups.values() for t in teams]
    counts = {t: [0] * len(_STAGES) for t in all_teams}

    for _ in range(n_iter):
        reached = _simulate_once(rng, groups, ratings)
        for team, furthest in reached.items():
            for idx in range(furthest + 1):  # cumulative: reaching SF implies reaching R32..SF
                counts[team][idx] += 1

    keys = ["reach_r32", "reach_r16", "reach_qf", "reach_sf", "reach_final", "win"]
    teams_out = {
        t: {key: round(counts[t][i] / n_iter, 4) for i, key in enumerate(keys)}
        for t in all_teams
    }
    ranked = dict(sorted(teams_out.items(), key=lambda kv: kv[1]["win"], reverse=True))
    champion = next(iter(ranked))
    return {"teams": ranked, "iterations": n_iter, "champion": champion}
