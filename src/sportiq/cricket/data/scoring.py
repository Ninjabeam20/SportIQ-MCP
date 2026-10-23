"""T20 fantasy scoring constants + per-component helpers.

Single source of truth for `dream11_solver`, `captain_score`, and
`form_index`. Values follow the official Dream11 T20 points table at
https://login.dream11.com/games/fantasy-cricket/how-to-play, as checked on
2026-10-10 (profile ``dream11-t20-2026-10-10``, the check date used as the
effective date). Announced-lineup and substitute (+4 each) points are not
modelled: they are per-selection, not per-innings.
"""

from __future__ import annotations

from dataclasses import dataclass

SCORING_PROFILE = "dream11-t20-2026-10-10"


@dataclass(frozen=True)
class T20Scoring:
    # Batting
    run: int = 1
    boundary_bonus: int = 4
    six_bonus: int = 6
    # Milestones: only the highest one reached scores (100 runs → +16, not 4+8+12+16).
    twenty_five_run_bonus: int = 4
    half_century_bonus: int = 8
    seventy_five_run_bonus: int = 12
    century_bonus: int = 16
    duck_penalty: int = -2  # BAT / ALL / WK-BAT only

    # Bowling
    dot_ball: int = 1
    wicket: int = 30  # excluding run out
    lbw_bowled_bonus: int = 8
    three_wicket_bonus: int = 4
    four_wicket_bonus: int = 8
    five_wicket_bonus: int = 12
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

# Strike-rate bonus buckets (only apply once a batter has faced >=10 balls;
# never to bowlers). Tuple = (lower_inclusive, upper_inclusive, bonus_points);
# the rate is rounded to 2 dp first so the published bounds leave no gaps.
SR_BUCKETS: tuple[tuple[float, float, int], ...] = (
    (170.01, float("inf"), 6),
    (150.01, 170.0, 4),
    (130.0, 150.0, 2),
    (60.0, 70.0, -2),
    (50.0, 59.99, -4),
    (float("-inf"), 49.99, -6),
)

# Economy buckets (only apply once a bowler has bowled >=2 overs). Official T20:
# below 5 → +6, 5-5.99 → +4, 6-7 → +2. Rounded to 2 dp before matching.
ECONOMY_BUCKETS: tuple[tuple[float, float, int], ...] = (
    (float("-inf"), 4.99, 6),
    (5.0, 5.99, 4),
    (6.0, 7.0, 2),
    (10.0, 11.0, -2),
    (11.01, 12.0, -4),
    (12.01, float("inf"), -6),
)

_BATTING_ROLES = {"BAT", "ALL", "WK-BAT", "WK"}


def strike_rate_bonus(runs: int, balls: int) -> int:
    if balls < 10:
        return 0
    sr = round((runs / balls) * 100, 2)
    for lo, hi, bonus in SR_BUCKETS:
        if lo <= sr <= hi:
            return bonus
    return 0


def economy_bonus(runs_conceded: int, overs: float) -> int:
    if overs < 2:
        return 0
    economy = round(runs_conceded / overs, 2)
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
    elif runs >= 75:
        pts += SCORING.seventy_five_run_bonus
    elif runs >= 50:
        pts += SCORING.half_century_bonus
    elif runs >= 25:
        pts += SCORING.twenty_five_run_bonus
    if runs == 0 and dismissed and role in _BATTING_ROLES:
        pts += SCORING.duck_penalty
    if role.upper() != "BOWL":  # strike-rate points: "except bowlers"
        pts += strike_rate_bonus(runs, balls)
    return pts


def bowling_points(
    wickets: int,
    lbw_or_bowled: int,
    maidens: int,
    runs_conceded: int,
    overs: float,
    dot_balls: int = 0,
) -> int:
    pts = wickets * SCORING.wicket
    pts += dot_balls * SCORING.dot_ball
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
        wickets, lbw_or_bowled, maidens, runs_conceded, overs, dot_balls,
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
            dot_balls=innings.get("dot_balls", 0),
        )
        + fielding_points(
            catches=innings.get("catches", 0),
            stumpings=innings.get("stumpings", 0),
            run_outs_direct=innings.get("run_outs_direct", 0),
            run_outs_indirect=innings.get("run_outs_indirect", 0),
        )
    )
