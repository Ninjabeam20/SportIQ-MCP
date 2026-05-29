---
title: "ADR-0008: Football Fallback Strategy + WC 2026 Format Encoding"
type: decision
tags: [football, fallback, monte-carlo, 2026-format]
sources: []
last_updated: 2026-05-29
related: [[api-football]], [[football-data-org]], [[static-seed]], [[bracket-sim]], [[football-simulate-bracket]]
---

# ADR-0008: Football Fallback Strategy + WC 2026 Format Encoding

## Status

Accepted — 2026-05-29 (Phase 4)

## Context

Phase 4 adds 6 RAW + 5 INTEL football tools, with `football_simulate_bracket` as flagship #3. Two decisions needed pinning down: the data-source ladder, and how to encode the **new 48-team World Cup 2026 format** — the single biggest correctness risk.

## Decision — data sources

- **API-Football** (`APIFOOTBALL_KEY`): primary for fixtures, standings, team stats, squads, scorers. 100 req/day shared budget. Constructor never raises; missing key -> `MissingCredentialsError`, chain walks past.
- **football-data.org** (`FOOTBALLDATA_KEY`, optional): free fallback for fixtures/standings/scorers. Token optional — public tier works without it. 10 req/min, 100/day.
- **Static seed** (`wc2026.json` + `elo_seed.json`): always-on terminator. Serves the group draw, the 48-team Elo ratings, and a synthesised group-stage schedule. Also the sole source for every INTEL tool (they need the draw + ratings).
- **Discipline (carried from F1 audit finding #2):** every fallback adapter in a chain shares the same call signature and returns the same normalised output shape, so a fallback never `TypeError`s or returns a foreign shape.

## Decision — WC 2026 format

The 2026 tournament is **48 teams, 12 groups of 4**. Advancement: **top 2 of each group + the 8 best third-placed teams → Round of 32**, then R32 → R16 → QF → SF → Final. This is encoded in:

- `wc2026.json` — 12 groups (A–L) partitioning 48 teams, plus the `format` block (`advance_per_group: 2`, `best_thirds: 8`, `knockout_start: "R32"`).
- `group_sim.py` — 4-team round-robin, FIFA tiebreakers.
- `bracket_sim.py` — ranks all 12 third-placed teams to pick the best 8, then a 32-team knockout.

We did **not** copy a 2022 (32-team / Round-of-16) bracket.

## Consequences / known simplifications

- **Bracket seeding:** the official 2026 third-place allocation table is not used. Qualifiers are strength-seeded (group points → GD → GF) into a standard 1-vs-N bracket. Deterministic under a fixed seed; exact FIFA slotting is a follow-up. The tested invariants (32 qualifiers/iteration, one champion/iteration, monotone round probabilities, ±2% convergence at ~10k) hold regardless.
- **Ratings are Elo seeds, not a live feed.** `lambdas_from_elo` maps an Elo edge to a Poisson goal supremacy. Re-seeding from a live rating feed is a future enhancement.
- **No squad rosters bundled** — the static squad terminator returns an empty-but-valid squad. Roster seed is a documented follow-up.
- **48-team draw is representative**, not the official draw (which is not fully known at build time). Swapping in the real draw is a single-file edit (`wc2026.json`).
