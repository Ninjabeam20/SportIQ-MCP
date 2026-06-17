---
title: Results State
type: model
tags: [football, live, name-join, standings, wc2026]
sources: [src/sportiq/football/models/results_state.py]
last_updated: 2026-06-16
related: [[live-conditioning]], [[bracket-sim]], [[group-sim]]
---

# Results State

Pure helper that maps the live WC 2026 fixture feed into our team-code space and
splits results into what's decided vs. still to play. The shared foundation under
[[live-conditioning]], the keyless `derived_standings` adapter, and the Elo nudge.

## What it produces

`build_results_state(fixtures, groups, teams)` returns a `ResultsState`:

- `groups[letter]` → `GroupResults(completed, remaining)`. `completed` entries are
  `(code_a, code_b, goals_a, goals_b)`; `remaining` are the unplayed pairings of
  the six round-robin matches.
- `knockout` → decided ties as `(code_a, code_b, winner_code)`.
- `completed_chrono` → every completed match in date order (for the Elo walk).
- `matched` / `dropped` → how many finished fixtures resolved vs. were skipped.

## Name join

Live fixtures carry team *names*; the sims use *codes*. `build_code_index`
indexes each team's name, `fifa_code`, and code, plus a small alias table for
known label variants (e.g. "Korea Republic"→KOR, "Côte d'Ivoire"/"Ivory Coast"
→CIV). Names are normalised (lowercase, accents stripped, non-alphanumerics
collapsed). An unresolved finished fixture is **dropped and counted**, never
raised — noisy upstream labels can degrade coverage but cannot crash a tool.

## Derived standings

`derived_standings(fixtures, groups, teams)` computes the group table (3/1/0
points, ordered points → GD → GF) from completed matches, in the same shape the
live standings adapters return. Backs the keyless `derived_standings` adapter so
`football_get_standings` works with zero API keys.
