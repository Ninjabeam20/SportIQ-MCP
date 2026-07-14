---
title: Group-Stage Monte Carlo
type: model
tags: [football, monte-carlo, group]
sources: [FIFA World Cup 2026 regulations]
last_updated: 2026-07-14
related: [[poisson-xg]], [[bracket-sim]], [[football-simulate-group]]
---

# Group-Stage Monte Carlo

Simulates all 12 four-team round-robins (6 matches each); match scores are sampled from
[[poisson-xg]] and completed fixtures are locked. One iteration ranks all third-placed teams
together, so the best-eight decision is shared by `football_simulate_group` and the bracket.

Within an equal-points cohort, the available FIFA order is head-to-head points → head-to-head
goal difference → head-to-head goals scored → overall goal difference → overall goals scored.
The model applies those head-to-head criteria once to the equal-points cohort rather than
iteratively reapplying them to a shrinking tied subset; this is a known approximation. Conduct and
latest FIFA ranking are not present in the model input, so ties that reach those fields use model
rating, then RNG only for equal ratings. Best-thirds use points → goal difference → goals scored,
with the same explicit fallback. Fallback rows are counted and exposed.
The implemented order follows FIFA's published [qualification and tiebreak
explainer](https://www.fifa.com/en/articles/groups-how-teams-qualify-tie-breakers) where the
model has the required fields.

- `simulate_group_once(rng, teams, ratings)` — one draw; returns ranked standings (used by [[bracket-sim]]).
- `simulate_group_stage(groups, ratings, n_iter, seed, results)` — aggregates all groups and
  returns `p_auto_advance`, `p_best_third_advance`, truthful `p_advance`, and fallback counts.
- `simulate_group(...)` — retained pure one-group helper where `p_advance` means top two only.

Invariants: automatic-advance mass per group is 2; best-third mass over the tournament is 8;
combined R32 mass is 32. Seeded calls are reproducible.
