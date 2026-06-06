"""Full-tournament Monte Carlo for WC 2026 (48 teams, 12 groups, R32 knockout).

Per iteration: simulate all 12 groups, take the top 2 of each plus the 8 best
third-placed teams (32 qualifiers), slot them into the **official FIFA 2026
knockout structure** (R32 template + Annex C best-thirds allocation + the fixed
R16->Final match tree, all from ``wc2026_bracket.json``), and play it to a
champion. Aggregating over many iterations yields each team's probability of
reaching every round and of winning the tournament.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from sportiq.football.models.elo import expected_score
from sportiq.football.models.group_sim import simulate_group_once
from sportiq.football.models.poisson_xg import lambdas_from_elo

_STAGES = ["R32", "R16", "QF", "SF", "Final", "Winner"]
# Round labels for the 5 knockout reductions starting from 32 qualifiers.
_KO_ROUNDS = ["R16", "QF", "SF", "Final", "Winner"]

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
# Official bracket structure, loaded once at import (see scripts/build_wc2026_bracket.py).
_BRACKET = json.loads((_DATA_DIR / "wc2026_bracket.json").read_text())


def _draw_qualifiers(
    rng: np.random.Generator,
    groups: dict[str, list[str]],
    ratings: dict[str, float],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Simulate all 12 groups. Return (winners, runners, best_thirds_by_group).

    ``winners``/``runners`` map every group letter to a team. ``best_thirds_by_group``
    maps only the 8 best third-placed groups (by points -> gd -> gf -> random) to their team.
    """
    winners: dict[str, str] = {}
    runners: dict[str, str] = {}
    thirds: list[dict] = []
    for letter, teams in groups.items():
        if len(teams) != 4:
            raise ValueError(
                f"Group {letter} must have exactly 4 teams (WC 2026 format); got {len(teams)}."
            )
        standings = simulate_group_once(rng, teams, ratings)
        winners[letter] = standings[0]["team"]
        runners[letter] = standings[1]["team"]
        third = dict(standings[2])
        third["group"] = letter
        thirds.append(third)

    best = sorted(
        thirds, key=lambda r: (r["points"], r["gd"], r["gf"], rng.random()), reverse=True
    )[:8]
    best_thirds = {r["group"]: r["team"] for r in best}
    return winners, runners, best_thirds


def _build_r32(
    winners: dict[str, str],
    runners: dict[str, str],
    best_thirds: dict[str, str],
) -> list[str]:
    """Resolve the official R32 template to 32 teams in bracket order.

    The returned list pairs adjacent entries (0,1), (2,3), ... as R32 matches, ordered so the
    existing round loop reproduces the official R16/QF/SF/final tree.
    """
    combo = "".join(sorted(best_thirds))
    alloc = _BRACKET["third_allocation"][combo]  # {winner_slot: third_group_letter}

    def base(slot: str) -> str | None:
        if slot[0] == "1":
            return winners[slot[1]]
        if slot[0] == "2":
            return runners[slot[1]]
        return None  # a "3.../" third slot, resolved against its paired winner slot

    current: list[str] = []
    for match_no in _BRACKET["bracket_order"]:
        m = _BRACKET["r32"][str(match_no)]
        s1, s2 = m["slot1"], m["slot2"]
        t1, t2 = base(s1), base(s2)
        if t1 is None:  # s1 is the third slot; s2 is its winner slot "1Y"
            t1 = best_thirds[alloc[s2]]
        if t2 is None:  # s2 is the third slot; s1 is its winner slot "1Y"
            t2 = best_thirds[alloc[s1]]
        current.extend([t1, t2])
    return current


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
    winners, runners, best_thirds = _draw_qualifiers(rng, groups, ratings)
    current = _build_r32(winners, runners, best_thirds)

    reached: dict[str, int] = {team: 0 for team in current}  # 0 == reached R32
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
