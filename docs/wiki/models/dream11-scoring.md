---
title: Dream11 T20 Scoring
type: model
tags: [cricket, dream11, scoring, t20]
sources: [src/sportiq/cricket/data/scoring.py, docs/audits/2026-10-10-sports-model-audit.md]
last_updated: 2026-10-22
related: [[dream11-solver]], [[captain-score]], [[cricket-build-dream11-team]], [[2026-10-22-full-audit]]
---

# Dream11 T20 Scoring

Single source of truth for fantasy-point arithmetic: `src/sportiq/cricket/data/scoring.py`, the frozen `T20Scoring` dataclass plus per-component helpers, versioned as profile `dream11-t20-2026-10-10`.

## Profile

Values follow the official Dream11 T20 points table at
`https://login.dream11.com/games/fantasy-cricket/how-to-play`, as checked on 2026-10-10 (the check date is
the profile's effective date). `SCORING_PROFILE` is reported in the Dream11 tool's `meta.scoring_profile`
and served by the `sportiq://cricket/scoring-profile` MCP resource. The audit's worked examples pin it: a
synthetic 100 off 50 balls with 8 fours and 6 sixes scores **190**, and a 3/25 spell with one bowled/LBW
wicket and 10 dots scores **114**. The values before 2026-10-22 were a scaled-down approximation (for
example a wicket at 25 and a four at +1) that gave 134 and 89 for the same examples.

Not modelled: the announced-lineup and playing-substitute points (+4 each), which are per selection, not
per innings.

## Constants

| Component | Value |
| :--- | :--- |
| Run | +1 |
| Boundary bonus | +4 |
| Six bonus | +6 |
| 25 / 50 / 75 / 100-run bonus | +4 / +8 / +12 / +16 (**highest milestone only**) |
| Duck penalty (BAT/ALL/WK-BAT only, dismissed for 0) | -2 |
| Dot ball | +1 |
| Wicket (excluding run-out) | +30 |
| LBW / bowled bonus | +8 (each) |
| 3 / 4 / 5-wicket haul | +4 / +8 / +12 (highest only) |
| Maiden over | +12 |
| Catch | +8 |
| 3-catch bonus | +4 |
| Stumping | +12 |
| Run-out (direct) | +12 |
| Run-out (indirect) | +6 |
| Captain multiplier | x2 |
| Vice-captain multiplier | x1.5 |

## Strike-rate buckets

Applied once a batter has faced ≥10 balls, and **never to bowlers** ("except bowlers"). The rate is
rounded to 2 dp before matching.

| SR | Bonus |
| :--- | :--- |
| ≥ 170.01 | +6 |
| 150.01–170 | +4 |
| 130–150 | +2 |
| 60–70 | -2 |
| 50–59.99 | -4 |
| ≤ 49.99 | -6 |

## Economy buckets

Applied once a bowler has bowled ≥2 overs; rounded to 2 dp before matching.

| Econ | Bonus |
| :--- | :--- |
| ≤ 4.99 | +6 |
| 5–5.99 | +4 |
| 6–7 | +2 |
| 10–11 | -2 |
| 11.01–12 | -4 |
| ≥ 12.01 | -6 |
