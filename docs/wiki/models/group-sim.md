---
title: Group-Stage Monte Carlo
type: model
tags: [football, monte-carlo, group]
sources: []
last_updated: 2026-05-29
related: [[poisson-xg]], [[bracket-sim]], [[football-simulate-group]]
---

# Group-Stage Monte Carlo

Simulates a 4-team round-robin (6 matches) many times; match scores sampled from [[poisson-xg]]. Standings use 3/1/0 points with FIFA-style tiebreakers (points -> goal difference -> goals for -> random).

- `simulate_group_once(rng, teams, ratings)` — one draw; returns ranked standings (used by [[bracket-sim]]).
- `simulate_group(teams, ratings, n_iter, seed)` — aggregates `p_first/second/third/fourth`, `p_advance` and `avg_points`.

Invariant: `p_advance` over the 4 teams sums to exactly 2 (two teams advance per group).
