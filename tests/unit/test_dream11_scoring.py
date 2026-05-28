"""Hand-checked arithmetic against the T20 scoring constants."""

from __future__ import annotations

from sportiq.cricket.data.scoring import (
    SCORING,
    batting_points,
    bowling_points,
    economy_bonus,
    fielding_points,
    innings_points,
    strike_rate_bonus,
)


def test_constants_match_plan():
    assert SCORING.run == 1
    assert SCORING.boundary_bonus == 1
    assert SCORING.six_bonus == 2
    assert SCORING.half_century_bonus == 4
    assert SCORING.century_bonus == 8
    assert SCORING.duck_penalty == -2
    assert SCORING.wicket == 25
    assert SCORING.lbw_bowled_bonus == 8
    assert SCORING.three_wicket_bonus == 4
    assert SCORING.four_wicket_bonus == 8
    assert SCORING.five_wicket_bonus == 16
    assert SCORING.maiden == 12
    assert SCORING.catch == 8
    assert SCORING.three_catch_bonus == 4
    assert SCORING.stumping == 12
    assert SCORING.run_out_direct == 12
    assert SCORING.run_out_indirect == 6
    assert SCORING.captain_multiplier == 2.0
    assert SCORING.vice_captain_multiplier == 1.5


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
    # 50 runs (50) + 5 fours (5) + 2 sixes (4) + half-century (4) + SR 166.7 → +4
    # Total = 50 + 5 + 4 + 4 + 4 = 67
    pts = batting_points(runs=50, fours=5, sixes=2, balls=30, role="BAT", dismissed=True)
    assert pts == 67


def test_batting_points_century_replaces_half_century_bonus():
    # 100 runs (100) + 8 fours (8) + 4 sixes (8) + century (8) + SR 100/60*100=166.67 → +4
    # Total = 100 + 8 + 8 + 8 + 4 = 128
    pts = batting_points(runs=100, fours=8, sixes=4, balls=60, role="BAT", dismissed=False)
    assert pts == 128


def test_duck_penalty_applies_only_to_batters_when_dismissed():
    # Dismissed BAT for 0 off 5 balls → 0 runs * 1 + 0 boundaries + 0 sixes + duck(-2) = -2
    # SR bucket ignored (<10 balls).
    assert batting_points(0, 0, 0, 5, role="BAT", dismissed=True) == -2
    # Not-out duck: no penalty.
    assert batting_points(0, 0, 0, 5, role="BAT", dismissed=False) == 0
    # Pure bowler does not get the duck penalty.
    assert batting_points(0, 0, 0, 5, role="BOWL", dismissed=True) == 0


def test_bowling_points_four_for_30_with_maiden():
    # 4 wickets (100) + 2 LBW (16) + 4-wkt bonus (8) + 1 maiden (12) + econ 30/4=7.5 → 0
    # Total = 100 + 16 + 8 + 12 = 136
    pts = bowling_points(wickets=4, lbw_or_bowled=2, maidens=1, runs_conceded=30, overs=4.0)
    assert pts == 136


def test_fielding_points_three_catches_get_bonus():
    # 3 catches * 8 = 24 + 3-catch-bonus (4) = 28
    assert fielding_points(catches=3, stumpings=0, run_outs_direct=0, run_outs_indirect=0) == 28


def test_innings_points_combines_all_disciplines():
    # All-rounder: 30 (bat) + 1 wkt + 1 catch
    # Bat: 30 + 3 fours (3) + 1 six (2) + SR 30/20*100=150 → bucket 130-150 = +2; total = 37
    # Bowl: 1 * 25 = 25
    # Field: 1 * 8 = 8
    # Total: 37 + 25 + 8 = 70
    innings = {
        "runs": 30, "fours": 3, "sixes": 1, "balls": 20, "dismissed": True,
        "wickets": 1, "lbw_or_bowled": 0, "maidens": 0, "runs_conceded": 24, "overs": 4.0,
        "catches": 1,
    }
    # economy 24/4=6.0 → bucket 5.01-6.0 = +4
    # Bowl total: 25 + 4 = 29
    # Grand total: 37 + 29 + 8 = 74
    assert innings_points(innings, role="ALL") == 74
