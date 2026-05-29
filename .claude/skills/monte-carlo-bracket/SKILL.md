---
name: monte-carlo-bracket
description: WC 2026 format (48 teams, 12 groups, top-2 + 8 best-thirds -> R32 knockout), the Poisson xG match engine, Elo seeding, and the group/bracket Monte Carlo. Load when working on football simulations.
when_to_use: When building or modifying football_simulate_bracket, football_simulate_group, the Poisson/Elo models, or the WC 2026 data.
---

# Monte Carlo Bracket Skill

## WC 2026 format (do NOT use the old 32-team bracket)

- **48 teams, 12 groups (A–L) of 4.**
- Group stage: 4-team round-robin, 3/1/0 points, tiebreakers points -> goal difference -> goals for -> random.
- Advancement: **top 2 of each group (24) + 8 best third-placed teams = 32 → Round of 32.**
- Knockout: R32 → R16 → QF → SF → Final (single elimination).
- Encoded in `football/data/wc2026.json` (`format` block + 12-group draw) and `elo_seed.json` (48 ratings).

## Match engine (poisson_xg.py)

- `lambdas_from_elo(elo_home, elo_away, home_advantage)`: supremacy = `(elo_home + adv - elo_away) * 0.004`; split around `avg_total_goals=2.6`; clamp to >= 0.05.
- `scoreline_matrix` / `outcome_probabilities`: independent Poisson grid (truncated at 10 goals); tril = home win, diagonal = draw, triu = away win.
- Home advantage at the World Cup is 0 (neutral venues) except for the hosts if you choose to model it.

## Elo (elo.py)

- `expected_score(Ra, Rb, H) = 1 / (1 + 10^(-((Ra+H)-Rb)/400))`. Used for the knockout shootout coin flip on a drawn tie.

## Sims

- `group_sim.simulate_group_once(rng, teams, ratings)` -> ranked standings (composed by the bracket sim).
- `group_sim.simulate_group(...)` -> `p_first/second/third/fourth`, `p_advance` (sums to exactly 2), `avg_points`.
- `bracket_sim.simulate_tournament(groups, ratings, n_iter, seed)` -> per-team `{reach_r32..win}` + `champion`.

## Invariants to preserve (tested)

- `p_advance` over a group's 4 teams == 2.
- `reach_r32` mass across all teams == 32 (exactly 32 qualify per iteration).
- `win` mass == 1 (one champion per iteration).
- Round probabilities monotone (reaching a later round implies reaching earlier ones).
- Champion title-probability stable within ±2% across seeds at ~10k iterations.
- Always pass a `seed` for reproducible output; `np.random.default_rng(seed)`.

## Seeding caveat

Qualifiers are strength-seeded (group points -> GD -> GF) into a standard 1-vs-N bracket — NOT the official FIFA third-place allocation table. Documented in ADR-0008; safe to refine later without breaking the invariants above.
