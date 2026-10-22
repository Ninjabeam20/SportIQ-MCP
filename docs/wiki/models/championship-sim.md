---
title: F1 Championship Simulator
type: model
tags: [f1, championship, monte-carlo, plackett-luce]
sources: [jolpica, docs/audits/2026-10-10-sports-model-audit.md]
last_updated: 2026-10-22
related: [[f1-simulate-championship]], [[f1-standings-chain]]
---

# F1 Championship Simulator

Pure model (`f1/models/championship_sim.py`) that samples the rest of an F1 season to estimate drivers' title probabilities, with exact elimination that sampling can never override.

## Maximum remaining points

`max_remaining_points(remaining, year)` = Σ over remaining rounds of race P1 (25, plus the fastest-lap point only before 2025) + sprint P1 (8) where a sprint is scheduled. Seven GPs with no sprints = 175.

## Elimination (exact)

A driver with `points_now + max_remaining < leader_points_now` is `eliminated` and gets `title_prob = 0.0`. When every rival is eliminated, the leader has clinched (`title_prob = 1.0`).

## Monte Carlo

- Strength: `points / rounds_completed`, floored at 0.5.
- Each race (and sprint) samples a full finishing order by Plackett–Luce with weights `strength ** 1.5`, using the Gumbel-max trick: `argsort(log w + Gumbel)` is an exact Plackett–Luce draw, vectorised over iterations with numpy.
- Points per position from `f1/data/points.py` (race top 10, sprint top 8). Fastest-lap points are not sampled.
- Champion per iteration = highest final total; equal totals break at random (countback is not modelled).
- Seeded runs are deterministic.

Plackett–Luce is scale-invariant in the weights, so `rounds_completed` only affects where the 0.5 floor applies.
