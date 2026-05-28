"""Project expected fantasy points for one player in one fixture.

Pure function with no I/O — feed it a player dict, a venue dict, an
opposition strength scalar, and a form score; get back a single float used by
the dream11 solver as the objective coefficient and by the captain
recommender for ranking.
"""

from __future__ import annotations

from sportiq.cricket.data.scoring import SCORING

# Baseline volume per archetype: T20 averages for a top-order player.
_BASELINE_RUNS = {"BAT": 35.0, "WK-BAT": 30.0, "ALL": 22.0, "BOWL": 8.0}
_BASELINE_WICKETS = {"BAT": 0.0, "WK-BAT": 0.0, "ALL": 1.0, "BOWL": 1.5}
# Fraction of a player's runs that come from boundaries / sixes (heuristic).
_BOUNDARY_RATE_BY_ROLE = {"BAT": 0.42, "WK-BAT": 0.45, "ALL": 0.40, "BOWL": 0.50}
_SIX_RATE_BY_ROLE = {"BAT": 0.12, "WK-BAT": 0.15, "ALL": 0.14, "BOWL": 0.08}

# Asymmetric pitch multipliers — a batting pitch helps batters more than it
# hurts bowlers, so an in-form batter outperforms an in-form bowler at Wankhede.
_PITCH_BAT_MULT = {"batting": 1.25, "balanced": 1.00, "bowling": 0.85}
_PITCH_BOWL_MULT = {"batting": 0.80, "balanced": 1.00, "bowling": 1.20}


def _form_multiplier(form_score: float) -> float:
    """Form score 0..100 → multiplier ~0.5..1.5."""
    return 0.5 + (max(0.0, min(100.0, form_score)) / 100.0)


def _opposition_multiplier(strength: float) -> float:
    """Strong opposition (1.0) reduces output; weak (0.0) boosts. Range 0.8..1.2."""
    s = max(0.0, min(1.0, strength))
    return 1.2 - 0.4 * s


def expected_points(
    player: dict,
    venue: dict,
    opposition_strength: float = 0.5,
    form_score: float = 50.0,
) -> float:
    """Return expected fantasy points for the player in this fixture.

    Args:
        player: must contain at least ``role`` (BAT/BOWL/ALL/WK-BAT).
        venue: must contain ``pitch_type`` (batting/bowling/balanced).
        opposition_strength: 0..1; 1 = elite opposition.
        form_score: 0..100 from compute_form_index().
    """
    role = player.get("role", "BAT").upper()
    if role == "WK":
        role = "WK-BAT"
    pitch_type = (venue or {}).get("pitch_type", "balanced")

    form_mult = _form_multiplier(form_score)
    opp_mult = _opposition_multiplier(opposition_strength)
    bat_pitch_mult = _PITCH_BAT_MULT.get(pitch_type, 1.0)
    bowl_pitch_mult = _PITCH_BOWL_MULT.get(pitch_type, 1.0)

    # Batting projection.
    base_runs = _BASELINE_RUNS.get(role, 10.0)
    exp_runs = base_runs * form_mult * bat_pitch_mult * opp_mult
    exp_fours = exp_runs * _BOUNDARY_RATE_BY_ROLE.get(role, 0.30) / 4.0
    exp_sixes = exp_runs * _SIX_RATE_BY_ROLE.get(role, 0.10) / 6.0

    bat_pts = (
        exp_runs * SCORING.run
        + exp_fours * SCORING.boundary_bonus
        + exp_sixes * SCORING.six_bonus
    )
    # Milestone bonuses, probabilistic (~odds we cross the threshold).
    if exp_runs >= 70:
        bat_pts += SCORING.century_bonus * 0.25
    if exp_runs >= 35:
        bat_pts += SCORING.half_century_bonus * 0.5

    # Bowling projection.
    base_wkts = _BASELINE_WICKETS.get(role, 0.0)
    exp_wkts = base_wkts * form_mult * bowl_pitch_mult * (1.0 - 0.2 * (opp_mult - 1.0))
    bowl_pts = exp_wkts * SCORING.wicket
    if exp_wkts >= 3:
        bowl_pts += SCORING.three_wicket_bonus

    # Fielding — small constant contribution; keepers get a stumping share.
    field_pts = SCORING.catch * 0.4
    if role in {"WK-BAT", "WK"}:
        field_pts += SCORING.stumping * 0.25

    return bat_pts + bowl_pts + field_pts
