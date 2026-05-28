---
title: Captain Score (expected_points)
type: model
tags: [cricket, dream11, projection]
sources: []
last_updated: 2026-05-28
related: [[dream11-solver]], [[dream11-scoring]], [[form-index]], [[pitch-report]]
---

# Captain Score (`expected_points`)

Pure function `expected_points(player, venue, opposition_strength, form_score) -> float`. Returns the projected fantasy-point total for one player in one fixture. Used as:

- The objective coefficient for every player in [[dream11-solver]].
- The ranking key for [[cricket-captain-recommendation]].

## What goes in

| Input | Type | Notes |
| :--- | :--- | :--- |
| `player` | dict | Needs `role` (BAT / BOWL / ALL / WK-BAT). |
| `venue` | dict | Needs `pitch_type` (batting / bowling / balanced). |
| `opposition_strength` | float 0..1 | 1 = elite opposition. Default 0.5. |
| `form_score` | float 0..100 | From [[form-index]]. Default 55. |

## The recipe

```
form_mult     = 0.5 + form_score / 100        # 0.5 .. 1.5
opp_mult      = 1.2 - 0.4 * opposition         # 0.8 .. 1.2
bat_pitch     = {batting: 1.25, balanced: 1.00, bowling: 0.85}
bowl_pitch    = {batting: 0.80, balanced: 1.00, bowling: 1.20}

expected_runs    = baseline_runs(role) * form * bat_pitch * opp
expected_wickets = baseline_wkts(role) * form * bowl_pitch * adj

points  = expected_runs * RUN
        + expected_fours * BOUNDARY_BONUS
        + expected_sixes * SIX_BONUS
        + (century * 0.25 if exp_runs ≥ 70)
        + (half_century * 0.5 if exp_runs ≥ 35)
        + expected_wickets * WICKET
        + (3wkt * if exp_wickets ≥ 3)
        + fielding_constant
        + stumping_share if WK
```

`baseline_runs` and `baseline_wkts` are role-specific T20 averages set at module-level constants.

## Why asymmetric pitch multipliers

A batting pitch helps batters more than it hurts bowlers (it's harder to reset a top-order than to give a bowler a bad day). `_PITCH_BAT_MULT["batting"]` is 1.25; `_PITCH_BOWL_MULT["batting"]` is 0.80 — net advantage of 0.45 to the bat. This ensures an in-form batter outscores a similarly in-form bowler at Wankhede.

## Tested ordering

`tests/unit/test_captain_score.py` asserts only the monotonicity / ordering guarantees — never an exact float magnitude — so the constants can be tuned without breaking tests.
