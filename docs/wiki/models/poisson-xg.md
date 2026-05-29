---
title: Poisson xG Match Engine
type: model
tags: [football, poisson, xg, scipy]
sources: []
last_updated: 2026-05-29
related: [[elo]], [[group-sim]], [[bracket-sim]], [[football-xg-model]], [[football-match-predictor]]
---

# Poisson xG Match Engine

Two teams' expected goals -> a `scipy.stats.poisson` scoreline matrix -> P(home win / draw / away win). The shared match engine for the xG tool, the group sim and the bracket sim.

## Expected goals
- `lambdas_from_elo(elo_home, elo_away, home_advantage)` — supremacy = `(elo_home + adv - elo_away) * 0.004`; split around an average total of 2.6 goals; clamped to >= 0.05.
- `lambdas_from_strength(...)` — Dixon-Coles style from attack/defense ratios when real rates exist.

## Scoreline -> outcome
`scoreline_matrix(lh, la)` is the (11x11) joint grid `P(home=i, away=j)` of independent Poissons (truncated at 10 goals). `outcome_probabilities` sums the lower triangle / diagonal / upper triangle. `most_likely_scoreline` returns the modal score.

Pure functions, no I/O.
