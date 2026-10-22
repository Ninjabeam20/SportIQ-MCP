"""Hand-checked arithmetic against the official Dream11 T20 profile (dream11-t20-2026-10-10)."""

from __future__ import annotations

from sportiq.cricket.data.scoring import (
    SCORING,
    SCORING_PROFILE,
    batting_points,
    bowling_points,
    economy_bonus,
    fielding_points,
    innings_points,
    strike_rate_bonus,
)


def test_constants_match_official_t20_profile():
    assert SCORING_PROFILE == "dream11-t20-2026-10-10"
    assert SCORING.run == 1
    assert SCORING.boundary_bonus == 4
    assert SCORING.six_bonus == 6
    assert SCORING.twenty_five_run_bonus == 4
    assert SCORING.half_century_bonus == 8
    assert SCORING.seventy_five_run_bonus == 12
    assert SCORING.century_bonus == 16
    assert SCORING.duck_penalty == -2
    assert SCORING.dot_ball == 1
    assert SCORING.wicket == 30
    assert SCORING.lbw_bowled_bonus == 8
    assert SCORING.three_wicket_bonus == 4
    assert SCORING.four_wicket_bonus == 8
    assert SCORING.five_wicket_bonus == 12
    assert SCORING.maiden == 12
    assert SCORING.catch == 8
    assert SCORING.three_catch_bonus == 4
    assert SCORING.stumping == 12
    assert SCORING.run_out_direct == 12
    assert SCORING.run_out_indirect == 6
    assert SCORING.captain_multiplier == 2.0
    assert SCORING.vice_captain_multiplier == 1.5


def test_batting_points_century_example_matches_official_t20():
    # Audit 2026-10-10 synthetic: 100 off 50, 8 fours, 6 sixes.
    # 100 + 8*4 + 6*6 + century 16 (highest milestone only) + SR 200 → +6 = 190
    assert batting_points(runs=100, fours=8, sixes=6, balls=50, role="BAT", dismissed=False) == 190


def test_bowling_points_three_wicket_example_matches_official_t20():
    # Audit 2026-10-10 synthetic: 3/25 in 4 overs, one bowled/LBW, 10 dots.
    # 3*30 + 8 + 3-wkt 4 + 10 dots + economy 6.25 → +2 = 114
    pts = bowling_points(
        wickets=3, lbw_or_bowled=1, maidens=0, runs_conceded=25, overs=4.0, dot_balls=10
    )
    assert pts == 114


def test_economy_bucket_bounds_match_official_t20():
    # Official: below 5 → +6; 5-5.99 → +4; 6-7 → +2.
    assert economy_bonus(20, 4.0) == 4  # 5.00
    assert economy_bonus(24, 4.0) == 2  # 6.00
    assert economy_bonus(19, 4.0) == 6  # 4.75


def test_strike_rate_points_never_apply_to_bowlers():
    # 5 off 12 balls = SR 41.7 → -6 for a batter, 0 for a bowler.
    assert batting_points(5, 0, 0, 12, role="BAT", dismissed=True) == 5 - 6
    assert batting_points(5, 0, 0, 12, role="BOWL", dismissed=True) == 5


def test_batting_milestone_25_and_75_bonuses():
    # 25 off 25 (SR 100, no SR points): 25 + 25-run bonus 4 = 29
    assert batting_points(25, 0, 0, 25, role="BAT", dismissed=True) == 29
    # 80 off 80 (SR 100): 80 + 75-run bonus 12 = 92
    assert batting_points(80, 0, 0, 80, role="BAT", dismissed=True) == 92


def test_strike_rate_bonus_high_aggressive():
    # 60 off 30 balls = 200 SR → +6 (above 170)
    assert strike_rate_bonus(60, 30) == 6


def test_strike_rate_bonus_in_140_bucket():
    # 70 off 50 balls = 140 SR → +2 (130-150)
    assert strike_rate_bonus(70, 50) == 2


def test_strike_rate_bonus_under_10_balls_ignored():
    # SR buckets only apply once 10+ balls have been faced.
    assert strike_rate_bonus(30, 9) == 0


def test_economy_under_5_gets_top_bonus():
    # 18 runs in 4 overs = 4.5 econ → +6
    assert economy_bonus(18, 4.0) == 6


def test_economy_under_2_overs_ignored():
    assert economy_bonus(20, 1.5) == 0


def test_batting_points_50_off_30():
    # 50 runs (50) + 5 fours (20) + 2 sixes (12) + half-century (8) + SR 166.7 → +4
    # Total = 50 + 20 + 12 + 8 + 4 = 94
    pts = batting_points(runs=50, fours=5, sixes=2, balls=30, role="BAT", dismissed=True)
    assert pts == 94


def test_batting_points_century_replaces_half_century_bonus():
    # 100 runs (100) + 8 fours (32) + 4 sixes (24) + century (16) + SR 166.67 → +4
    # Total = 100 + 32 + 24 + 16 + 4 = 176
    pts = batting_points(runs=100, fours=8, sixes=4, balls=60, role="BAT", dismissed=False)
    assert pts == 176


def test_duck_penalty_applies_only_to_batters_when_dismissed():
    # Dismissed BAT for 0 off 5 balls → 0 runs * 1 + 0 boundaries + 0 sixes + duck(-2) = -2
    # SR bucket ignored (<10 balls).
    assert batting_points(0, 0, 0, 5, role="BAT", dismissed=True) == -2
    # Not-out duck: no penalty.
    assert batting_points(0, 0, 0, 5, role="BAT", dismissed=False) == 0
    # Pure bowler does not get the duck penalty.
    assert batting_points(0, 0, 0, 5, role="BOWL", dismissed=True) == 0


def test_bowling_points_four_for_30_with_maiden():
    # 4 wickets (120) + 2 LBW (16) + 4-wkt bonus (8) + 1 maiden (12) + econ 30/4=7.5 → 0
    # Total = 120 + 16 + 8 + 12 = 156
    pts = bowling_points(wickets=4, lbw_or_bowled=2, maidens=1, runs_conceded=30, overs=4.0)
    assert pts == 156


def test_fielding_points_three_catches_get_bonus():
    # 3 catches * 8 = 24 + 3-catch-bonus (4) = 28
    assert fielding_points(catches=3, stumpings=0, run_outs_direct=0, run_outs_indirect=0) == 28


def test_innings_points_combines_all_disciplines():
    # All-rounder: 30 (bat) + 1 wkt + 1 catch
    # Bat: 30 + 3 fours (12) + 1 six (6) + 25-run bonus (4) + SR 150 → +2; total = 54
    # Bowl: 1 * 30 = 30
    # Field: 1 * 8 = 8
    innings = {
        "runs": 30,
        "fours": 3,
        "sixes": 1,
        "balls": 20,
        "dismissed": True,
        "wickets": 1,
        "lbw_or_bowled": 0,
        "maidens": 0,
        "runs_conceded": 24,
        "overs": 4.0,
        "catches": 1,
    }
    # economy 24/4=6.0 → official bucket 6-7 = +2
    # Bowl total: 30 + 2 = 32
    # Grand total: 54 + 32 + 8 = 94
    assert innings_points(innings, role="ALL") == 94
