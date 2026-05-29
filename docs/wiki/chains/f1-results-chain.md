---
title: F1 Results Chain
type: chain
tags: [f1, race-results]
sources: []
last_updated: 2026-05-29
related: [[jolpica]], [[f1-get-race-results]]
---

# F1 Results Chain

`FallbackChain` that powers `f1_get_race_results`. Added in Phase 3.1 (audit finding #3) — previously `f1_get_race_results` was a mislabeled stub pointing at the drivers chain.

## Resolution order

`jolpica` (only source)

| Adapter | Enabled by default |
| :--- | :--- |
| [[jolpica]] | Yes — no credentials required |

Keyed by `year` + `round` (Ergast/Jolpica `f1/{year}/{round}/results.json`), not `session_key`.

## TTLs

- Fresh: 24h
- Stale ceiling: 7d

## Cache key

`sportiq:f1:results:{year}:{round}`
