---
title: F1 Schedule Chain
type: chain
tags: [f1, jolpica, schedule, calendar]
sources: [src/sportiq/f1/chains.py, src/sportiq/f1/adapters/jolpica.py]
last_updated: 2026-10-22
related: [[jolpica]], [[f1-simulate-championship]], [[championship-sim]], [[f1-standings-chain]]
---

# F1 Schedule Chain

`FallbackChain` that returns one season's F1 calendar — each round's number, name, date and whether it has a sprint — used by [[f1-simulate-championship]] to count the rounds still to run.

## Resolution order
[[jolpica]] `GET /ergast/f1/{year}.json` (only source) → stale cache.

## TTLs
- Fresh: 6h
- Stale ceiling: 24h

The static fixtures/schedule class from `.claude/rules/caching-policy.md`.

## Cache key
`sportiq:f1:schedule:{year}`

## Output
`{season, races: [{round, raceName, date, sprint}]}`. `sprint` is true when the Jolpica race carries a
`Sprint` key. An empty race table raises `NotFoundError`, so emptiness is never cached. The recorded
response for tests is `tests/fixtures/jolpica/schedule_2026.json` (keyless, 2026-10-22).
