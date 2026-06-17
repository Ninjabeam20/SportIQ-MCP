---
title: Live Result Conditioning
type: model
tags: [football, simulation, monte-carlo, elo, live, wc2026]
sources: [src/sportiq/football/models/results_state.py, src/sportiq/football/models/elo_live.py]
last_updated: 2026-06-16
related: [[bracket-sim]], [[group-sim]], [[elo]], [[results-state]]
---

# Live Result Conditioning

Makes the WC 2026 football simulations move with the tournament instead of
replaying a frozen pre-tournament seed. As real matches finish, the sims lock in
what has happened and only Monte-Carlo what hasn't.

## Why

`elo_seed.json` is frozen at package-build time and the bracket sim previously
re-simulated all 12 groups from scratch every run — so an eliminated team still
showed a title chance and a group winner was treated as if the group hadn't
started. Probabilities never moved as matches were played.

## How it works

1. **`results_state.build_results_state(fixtures, groups, teams)`** ([[results-state]])
   joins the live fixture feed (team *names*) onto our team *codes* via the
   `wc2026.json` `teams` metadata (name + fifa_code, accent/alias-normalised),
   then partitions each group's six round-robin pairings into **completed**
   (locked, with scores) and **remaining** (still sampled). Decided knockout ties
   become locked winners. Unmatched finished fixtures are **dropped and counted**,
   never crashed.
2. **[[group-sim]] / [[bracket-sim]]** accept an optional `known` / `results`
   argument. Completed matches contribute fixed points/GF/GA; only remaining
   matches are sampled. A fully-played group is deterministic; an eliminated team
   falls to `p_advance == 0` naturally. `None` reproduces the original
   from-scratch behaviour (backward compatible).
3. The intel tools (`football_simulate_group`, `football_simulate_bracket`,
   `football_knockout_path`) fetch fixtures alongside the draw, build the state,
   and surface `meta.conditioned_matches` (+ `fixtures_dropped`). If no fixture
   source is available they degrade to the from-scratch sim with a `meta.note`.

## In-tournament Elo nudge (opt-in)

[[elo]]-based `elo_live.nudge_ratings` walks the frozen seed forward from the
completed matches (chronologically, standard K=30 update) so the *unplayed*
matches the sims still sample — and the single-match `football_match_predictor` /
`football_xg_model` — reflect current form. Gated behind
`SPORTIQ_FOOTBALL_LIVE_ELO=1` (`settings.football_live_elo`, default off); it
**never rewrites `elo_seed.json`** (respects the D1 "don't reseed" finding). No
double-counting: played group matches are already locked by conditioning, so the
nudge only informs future-match strength. Tools set `meta.live_elo: true` when
applied.

## Known limitation

A knockout tie between two teams from the *same* group can't be distinguished
from their group-stage meeting by membership alone, so it is read as the group
fixture. Cross-group knockout ties (the overwhelming majority) classify
correctly.
