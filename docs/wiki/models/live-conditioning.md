---
title: Live Result Conditioning
type: model
tags: [football, simulation, monte-carlo, elo, live, wc2026]
sources: [src/sportiq/football/models/results_state.py, src/sportiq/football/models/elo_live.py]
last_updated: 2026-10-22
related: [[bracket-sim]], [[group-sim]], [[elo]], [[results-state]], [[openfootball]], [[football-what-if]]
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
   preserves provider `match_id`, `stage`, and explicit `winner`, then partitions each group's
   six round-robin pairings into **completed**
   (locked, with scores) and **remaining** (still sampled). Decided knockout ties
   become locked winners. Reports deduplicate by provider match ID, or by stage class + pairing
   when no ID exists. Unmatched or undecidable finished fixtures are **dropped and counted**,
   never crashed. A level `PEN` result locks only when the provider supplies a winner.
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

## Stage classification

Explicit group tokens (`GROUP`, `GROUP_STAGE`, `MATCHDAY`, and provider group labels) classify as
group; other nonempty stages classify as knockout. Same-group membership is used only when legacy
payloads omit stage. Consequently a later knockout between two teams from the same original group
no longer overwrites the group result, and both remain in chronological Elo input.

## Simulation mode (`meta.mode`)

Every conditioned sim reports one of three modes:

| `meta.mode` | When |
| :-- | :-- |
| `completed` | the state has a `champion` (the winner of a finished fixture whose stage is the final); `meta.champion` is set |
| `in_progress` | real results were matched but there is no champion yet |
| `pre_tournament_prior` | no state, nothing matched, or the fixtures came from the scores-less static seed; a note says this is a reconstructed pre-tournament simulation, not the current state |

In `completed` mode the bracket and knockout-path tools skip the Monte Carlo and return the exact rounds
from [[bracket-sim]] (`meta.iterations == 0`). [[football-what-if]] uses `meta.mode = "what_if"` instead.

## Post-final data (2026-10-22 fixes)

- [[openfootball]] now keeps extra-time and penalty scores and the winner's name, so the 0–0-after-90
  final and the four shootouts lock as decided ties.
- [[results-state]] aliases `Cape Verde` / `Cabo Verde` → CPV and `DR Congo` / `Congo DR` → COD, the
  spellings openfootball uses.
- Team participation is checked against the draw (not the rating table), and the draw's KSA key is
  aliased to the rating seed's SAU.
- With `SPORTIQ_FOOTBALL_LIVE_ELO=1` the single-match tools also pass the fixtures result to
  `staleness_meta`, so a stale fixtures feed is reported instead of swallowed.
