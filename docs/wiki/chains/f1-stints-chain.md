---
title: F1 Stints Chain
type: chain
tags: [f1, stints]
sources: []
last_updated: 2026-10-22
related: [[openf1]], [[f1-predict-pit-strategy]]
---

# F1 Stints Chain

`FallbackChain` that powers stint data for `f1_predict_pit_strategy`.

## Resolution order

`openf1`

| Adapter | Enabled by default |
| :--- | :--- |
| [[openf1]] | Yes for historical data; live access needs paid OpenF1 auth (not wired) |

## TTLs

- Fresh: 24h
- Stale ceiling: 7d

Keyless OpenF1 serves completed sessions only (live auth is not wired), and a completed session's
laps and stints never change, so they use the completed-session class from
`.claude/rules/caching-policy.md` (D18, 2026-10-22; previously 10s / 60s).

## Cache key

`sportiq:f1:stints:{session_key}:{driver_number_or_none}`
