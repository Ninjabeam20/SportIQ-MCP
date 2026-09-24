---
title: F1 Drivers Chain
type: chain
tags: [f1, drivers]
sources: []
last_updated: 2026-09-25
related: [[openf1]], [[f1-get-drivers]], [[f1-get-race-results]]
---

# F1 Drivers Chain

`FallbackChain` that powers `f1_get_drivers` and `f1_get_race_results`.

## Resolution order

`openf1`

| Adapter | Enabled by default |
| :--- | :--- |
| [[openf1]] | Yes for historical data; live access needs paid OpenF1 auth (not wired) |

## TTLs

- Fresh: 24h
- Stale ceiling: 7d

## Cache key

`sportiq:f1:drivers:{session_key}`
