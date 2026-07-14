---
name: monte-carlo-bracket
description: WC 2026 format (48 teams, 12 groups, top-2 + 8 best-thirds -> R32 knockout), the Poisson xG match engine, Elo seeding, and the group/bracket Monte Carlo. Load when working on football simulations.
when_to_use: When building or modifying football_simulate_bracket, football_simulate_group, the Poisson/Elo models, or the WC 2026 data.
---

# Monte Carlo Bracket Skill

## WC 2026 format (do NOT use the old 32-team bracket)

- **48 teams, 12 groups (A–L) of 4.**
- Group stage: 4-team round-robin, 3/1/0 points. Equal-points cohorts use available FIFA fields:
  head-to-head points → head-to-head GD → head-to-head goals → overall GD → overall GF. Missing
  conduct/latest-ranking data falls back visibly to model rating, then RNG only for equal ratings.
- Advancement: **top 2 of each group (24) + 8 best third-placed teams = 32 → Round of 32.**
- Knockout: R32 → R16 → QF → SF → Final (single elimination).
- Encoded in `football/data/wc2026.json`, `elo_seed.json`, and `wc2026_bracket.json` (official
  R32 template, fixed tree, and all 495 best-third group combinations from Annex C).

## Match engine (poisson_xg.py)

- `lambdas_from_elo(elo_home, elo_away, home_advantage)`: supremacy = `(elo_home + adv - elo_away) * 0.004`; split around `avg_total_goals=2.6`; clamp to >= 0.05.
- `scoreline_matrix` / `outcome_probabilities`: independent Poisson grid (truncated at 10 goals); tril = home win, diagonal = draw, triu = away win.
- Home advantage at the World Cup is 0 (neutral venues) except for the hosts if you choose to model it.

## Elo (elo.py)

- `expected_score(Ra, Rb, H) = 1 / (1 + 10^(-((Ra+H)-Rb)/400))`. Used for the knockout shootout coin flip on a drawn tie.

## Sims

- `group_sim.simulate_group_once(rng, teams, ratings)` -> ranked standings (composed by the bracket sim).
- `group_sim.simulate_group_stage(...)` -> all 12 groups, contextual best thirds, per-team
  `p_auto_advance`, `p_best_third_advance`, combined `p_advance`, and fallback counts.
- `bracket_sim.simulate_tournament(groups, ratings, n_iter, seed)` -> per-team `{reach_r32..win}` + `champion`.

Fixture conditioning preserves provider `match_id`, `stage`, and explicit `winner`. Deduplicate by
ID, otherwise stage class + pairing; never let a same-pair knockout overwrite its group result.
Level knockout scores lock only with an explicit penalty winner.

## Invariants to preserve (tested)

- Automatic-advance mass over each group's 4 teams == 2.
- Best-third advance mass across all 12 groups == 8.
- `reach_r32` mass across all teams == 32 (exactly 32 qualify per iteration).
- `win` mass == 1 (one champion per iteration).
- Round probabilities monotone (reaching a later round implies reaching earlier ones).
- Champion title-probability stable within ±2% across seeds at ~10k iterations.
- Always pass a `seed` for reproducible output; `np.random.default_rng(seed)`.

## Official allocation and fallback caveat

Do not strength-seed or rebuild a generic 1-vs-N bracket. `_build_r32` must use the committed
official template and 495-row allocation. Conduct/latest-ranking inputs remain unavailable; keep
the model-rating fallback counted and exposed rather than silently calling it an official field.
Head-to-head criteria are currently applied once to the equal-points cohort rather than reapplied
iteratively to a shrinking tied subset; retain this explicit modeling approximation.
