"""Dream11 11-player + C/VC selection as a binary ILP.

CBC via PuLP. Pure function — callers feed candidates with projected points;
the solver returns the optimal squad under Dream11 T20 constraints.
"""

from __future__ import annotations

from pulp import (
    COIN_CMD,
    LpBinary,
    LpMaximize,
    LpProblem,
    LpStatus,
    LpVariable,
    lpSum,
)

from sportiq.core.errors import InvalidInputError
from sportiq.cricket.data.scoring import SCORING

# Phase 2 ships the "balanced" strategy only. Aggressive / differential tuning
# land in 2.1 as different (lo, hi) tuples per role.
_STRATEGY_ROLE_BOUNDS: dict[str, dict[str, tuple[int, int]]] = {
    "balanced": {
        "WK-BAT": (1, 4),
        "BAT": (3, 5),
        "ALL": (1, 3),
        "BOWL": (3, 5),
    },
}

_WK_ROLE_NAMES = {"WK-BAT", "WK"}


def _role_members(candidates: list[dict], role: str) -> list[int]:
    if role == "WK-BAT":
        return [i for i, c in enumerate(candidates) if c.get("role") in _WK_ROLE_NAMES]
    return [i for i, c in enumerate(candidates) if c.get("role") == role]


def solve(candidates: list[dict], strategy: str = "balanced") -> dict:
    """Pick the optimal Dream11 XI + captain + vice-captain.

    Args:
        candidates: list of player dicts with keys
            ``name`` (str), ``role`` (BAT/BOWL/ALL/WK-BAT),
            ``credits`` (float), ``projected_points`` (float), ``team`` (str).
        strategy: only ``"balanced"`` for Phase 2.

    Returns:
        {
            "players": [11 picked candidate dicts],
            "captain": str (picked player name),
            "vice_captain": str,
            "total_credits": float,
            "total_projected_points": float (incl. C x2 and VC x1.5 boosts),
        }

    Raises:
        InvalidInputError: < 11 candidates, unknown strategy, or no feasible
            XI under the constraints (e.g. credits over-budget,
            team-cap violation, missing keeper).
    """
    if strategy not in _STRATEGY_ROLE_BOUNDS:
        raise InvalidInputError(
            f"Unknown strategy {strategy!r}; choices: {sorted(_STRATEGY_ROLE_BOUNDS)}"
        )
    if len(candidates) < 11:
        raise InvalidInputError(
            f"Need >=11 candidates; got {len(candidates)}"
        )

    n = len(candidates)
    role_bounds = _STRATEGY_ROLE_BOUNDS[strategy]

    prob = LpProblem("dream11_xi", LpMaximize)
    x = [LpVariable(f"x_{i}", cat=LpBinary) for i in range(n)]
    cap = [LpVariable(f"c_{i}", cat=LpBinary) for i in range(n)]
    vc = [LpVariable(f"v_{i}", cat=LpBinary) for i in range(n)]

    # Exactly 11 in the XI.
    prob += lpSum(x) == 11, "squad_size"

    # Credit cap.
    prob += (
        lpSum(float(candidates[i].get("credits", 0)) * x[i] for i in range(n)) <= 100,
        "credit_cap",
    )

    # Per-team cap (no more than 7 from a single team).
    teams = {c.get("team", "") for c in candidates}
    for team in teams:
        members = [i for i in range(n) if candidates[i].get("team") == team]
        prob += lpSum(x[i] for i in members) <= 7, f"team_cap_{team}"

    # Role mix.
    for role, (lo, hi) in role_bounds.items():
        members = _role_members(candidates, role)
        prob += lpSum(x[i] for i in members) >= lo, f"role_min_{role}"
        prob += lpSum(x[i] for i in members) <= hi, f"role_max_{role}"

    # Captain / vice-captain selection.
    prob += lpSum(cap) == 1, "one_captain"
    prob += lpSum(vc) == 1, "one_vc"
    for i in range(n):
        prob += cap[i] + vc[i] <= 1, f"cv_disjoint_{i}"
        prob += cap[i] <= x[i], f"c_in_xi_{i}"
        prob += vc[i] <= x[i], f"v_in_xi_{i}"

    # Objective: base points + captain extra (1x extra -> x2 effective)
    # + vice-captain extra (0.5x extra -> x1.5 effective).
    c_bonus = SCORING.captain_multiplier - 1.0
    v_bonus = SCORING.vice_captain_multiplier - 1.0
    pp = [float(c.get("projected_points", 0)) for c in candidates]
    prob += lpSum(
        pp[i] * x[i] + pp[i] * cap[i] * c_bonus + pp[i] * vc[i] * v_bonus
        for i in range(n)
    )

    # COIN_CMD picks the `cbc` binary off PATH (brew install cbc on macOS arm64).
    status = prob.solve(COIN_CMD(msg=False))
    if LpStatus[status] != "Optimal":
        raise InvalidInputError(
            f"No feasible Dream11 XI under constraints: {LpStatus[status]}"
        )

    picked_idx = [i for i in range(n) if (x[i].value() or 0) > 0.5]
    captain_idx = next(i for i in range(n) if (cap[i].value() or 0) > 0.5)
    vc_idx = next(i for i in range(n) if (vc[i].value() or 0) > 0.5)

    picked = [candidates[i] for i in picked_idx]
    total_credits = sum(float(p.get("credits", 0)) for p in picked)
    base_points = sum(float(p.get("projected_points", 0)) for p in picked)
    total_points = (
        base_points
        + float(candidates[captain_idx].get("projected_points", 0)) * c_bonus
        + float(candidates[vc_idx].get("projected_points", 0)) * v_bonus
    )

    return {
        "players": picked,
        "captain": candidates[captain_idx]["name"],
        "vice_captain": candidates[vc_idx]["name"],
        "total_credits": round(total_credits, 2),
        "total_projected_points": round(total_points, 2),
    }
