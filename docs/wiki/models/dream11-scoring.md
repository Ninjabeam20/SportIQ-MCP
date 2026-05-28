---
title: Dream11 T20 Scoring
type: model
tags: [cricket, dream11, scoring, t20]
sources: []
last_updated: 2026-05-28
related: [[dream11-solver]], [[captain-score]], [[cricket-build-dream11-team]]
---

# Dream11 T20 Scoring

Single source of truth for fantasy-point arithmetic. Lives at `src/sportiq/cricket/data/scoring.py` as the frozen `T20Scoring` dataclass + per-component helpers.

## Constants

| Component | Value |
| :--- | :--- |
| Run | +1 |
| Boundary bonus | +1 |
| Six bonus | +2 |
| Half-century bonus (50+) | +4 |
| Century bonus (100+) | +8 |
| Duck penalty (BAT/ALL/WK only, dismissed for 0) | -2 |
| Wicket | +25 |
| LBW / bowled bonus | +8 (each) |
| 3-wicket haul | +4 |
| 4-wicket haul | +8 |
| 5-wicket haul | +16 |
| Maiden over | +12 |
| Catch | +8 |
| 3-catch bonus | +4 |
| Stumping | +12 |
| Run-out (direct) | +12 |
| Run-out (indirect) | +6 |
| Captain multiplier | x2 |
| Vice-captain multiplier | x1.5 |

## Strike-rate buckets

Applied only once a batter has faced ≥10 balls.

| SR | Bonus |
| :--- | :--- |
| > 170 | +6 |
| 150.01-170 | +4 |
| 130-150 | +2 |
| 60-70 | -2 |
| 50-59.99 | -4 |
| < 50 | -6 |

## Economy buckets

Applied only once a bowler has bowled ≥2 overs.

| Econ | Bonus |
| :--- | :--- |
| ≤ 5 | +6 |
| 5.01-6 | +4 |
| 6.01-7 | +2 |
| 10-11 | -2 |
| 11.01-12 | -4 |
| > 12 | -6 |

## Note on simplification

Real Dream11 awards larger absolute numbers (e.g. +50 for a half-century, +100 for a century). The relative *weights* match what [[dream11-solver]] needs — what matters is the ordering between roles, not the headline magnitudes.
