"""T20 fantasy scoring constants + per-component helpers.

Single source of truth for `dream11_solver`, `captain_score`, and
`form_index`. Values are simplified per Phase 2 plan; the live Dream11
table awards larger numbers but the relative weights match.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class T20Scoring:
    # Batting
    run: int = 1
    boundary_bonus: int = 1
    six_bonus: int = 2
    half_century_bonus: int = 4
    century_bonus: int = 8
    duck_penalty: int = -2  # BAT / ALL / WK-BAT only

    # Bowling
    wicket: int = 25
    lbw_bowled_bonus: int = 8
    three_wicket_bonus: int = 4
    four_wicket_bonus: int = 8
    five_wicket_bonus: int = 16
    maiden: int = 12

    # Fielding
    catch: int = 8
    three_catch_bonus: int = 4
    stumping: int = 12
    run_out_direct: int = 12
    run_out_indirect: int = 6

    # Multipliers (captain/vc fantasy boost on top of base points)
    captain_multiplier: float = 2.0
    vice_captain_multiplier: float = 1.5


SCORING = T20Scoring()

# Strike-rate bonus buckets (only apply once a batter has faced >=10 balls).
# Tuple = (lower_inclusive, upper_inclusive, bonus_points).
SR_BUCKETS: tuple[tuple[float, float, int], ...] = (
    (170.01, float("inf"), 6),
    (150.01, 170.0, 4),
    (130.0, 150.0, 2),
    (60.0, 70.0, -2),
    (50.0, 59.99, -4),
    (float("-inf"), 49.99, -6),
)

# Economy buckets (only apply once a bowler has bowled >=2 overs).
ECONOMY_BUCKETS: tuple[tuple[float, float, int], ...] = (
    (float("-inf"), 5.0, 6),
    (5.01, 6.0, 4),
    (6.01, 7.0, 2),
    (10.0, 11.0, -2),
    (11.01, 12.0, -4),
    (12.01, float("inf"), -6),
)

_BATTING_ROLES = {"BAT", "ALL", "WK-BAT", "WK"}


def strike_rate_bonus(runs: int, balls: int) -> int:
    if balls < 10:
        return 0
    sr = (runs / balls) * 100
    for lo, hi, bonus in SR_BUCKETS:
        if lo <= sr <= hi:
            return bonus
    return 0


def economy_bonus(runs_conceded: int, overs: float) -> int:
    if overs < 2:
        return 0
    economy = runs_conceded / overs
    for lo, hi, bonus in ECONOMY_BUCKETS:
        if lo <= economy <= hi:
            return bonus
    return 0


def batting_points(
    runs: int, fours: int, sixes: int, balls: int, role: str, dismissed: bool
) -> int:
    pts = runs * SCORING.run
    pts += fours * SCORING.boundary_bonus
    pts += sixes * SCORING.six_bonus
    if runs >= 100:
        pts += SCORING.century_bonus
    elif runs >= 50:
        pts += SCORING.half_century_bonus
    if runs == 0 and dismissed and role in _BATTING_ROLES:
        pts += SCORING.duck_penalty
    pts += strike_rate_bonus(runs, balls)
    return pts


def bowling_points(
    wickets: int, lbw_or_bowled: int, maidens: int, runs_conceded: int, overs: float
) -> int:
    pts = wickets * SCORING.wicket
    pts += lbw_or_bowled * SCORING.lbw_bowled_bonus
    if wickets >= 5:
        pts += SCORING.five_wicket_bonus
    elif wickets >= 4:
        pts += SCORING.four_wicket_bonus
    elif wickets >= 3:
        pts += SCORING.three_wicket_bonus
    pts += maidens * SCORING.maiden
    pts += economy_bonus(runs_conceded, overs)
    return pts


def fielding_points(
    catches: int, stumpings: int, run_outs_direct: int, run_outs_indirect: int
) -> int:
    pts = catches * SCORING.catch
    if catches >= 3:
        pts += SCORING.three_catch_bonus
    pts += stumpings * SCORING.stumping
    pts += run_outs_direct * SCORING.run_out_direct
    pts += run_outs_indirect * SCORING.run_out_indirect
    return pts


def innings_points(innings: dict, role: str) -> int:
    """Sum batting + bowling + fielding components for a single innings.

    Expected keys (all optional, default 0/False):
        runs, fours, sixes, balls, dismissed,
        wickets, lbw_or_bowled, maidens, runs_conceded, overs,
        catches, stumpings, run_outs_direct, run_outs_indirect.
    """
    return (
        batting_points(
            runs=innings.get("runs", 0),
            fours=innings.get("fours", 0),
            sixes=innings.get("sixes", 0),
            balls=innings.get("balls", 0),
            role=role,
            dismissed=innings.get("dismissed", False),
        )
        + bowling_points(
            wickets=innings.get("wickets", 0),
            lbw_or_bowled=innings.get("lbw_or_bowled", 0),
            maidens=innings.get("maidens", 0),
            runs_conceded=innings.get("runs_conceded", 0),
            overs=innings.get("overs", 0),
        )
        + fielding_points(
            catches=innings.get("catches", 0),
            stumpings=innings.get("stumpings", 0),
            run_outs_direct=innings.get("run_outs_direct", 0),
            run_outs_indirect=innings.get("run_outs_indirect", 0),
        )
    )
