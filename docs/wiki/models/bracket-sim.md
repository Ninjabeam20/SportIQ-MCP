---
title: Tournament Monte Carlo (flagship)
type: model
tags: [football, monte-carlo, bracket, 2026-format]
sources: []
last_updated: 2026-05-29
related: [[group-sim]], [[poisson-xg]], [[elo]], [[football-simulate-bracket]], [[0008-football-fallback-strategy]]
---

# Tournament Monte Carlo (flagship engine)

Drives `football_simulate_bracket`. Per iteration: simulate all **12 groups**, take the **top 2 + 8 best third-placed** teams (32 qualifiers — the 2026 format), strength-seed them into a single-elimination bracket, and play it to a champion. Aggregating gives each team's probability of reaching every round and winning.

## Knockout
- Ties sampled from [[poisson-xg]]; draws after normal time go to a shootout weighted by [[elo]] `expected_score`.
- `_seed_order(n)` builds the standard 1-vs-N bracket so top seeds meet late.

## Seeding caveat
The official 2026 third-place allocation table is **not** used; qualifiers are strength-seeded (group points -> GD -> GF). Deterministic under a fixed seed; exact FIFA slotting is a documented follow-up. See [[0008-football-fallback-strategy]].

## Invariants (tested)
- `reach_r32` mass across teams == 32 (exactly 32 qualify each iteration).
- `win` mass == 1 (one champion per iteration).
- Round probabilities are monotone; champion title-probability is stable (±2%) across seeds at ~10k iterations.
