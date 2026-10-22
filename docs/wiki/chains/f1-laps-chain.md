---
title: F1 Laps Chain
type: chain
tags: [f1, laps]
sources: []
last_updated: 2026-10-22
related: [[openf1]], [[fastf1]], [[f1-get-lap-times]], [[f1-tyre-degradation]], [[f1-undercut-window]], [[f1-head-to-head-pace]], [[f1-predict-pit-strategy]]
---

# F1 Laps Chain

`FallbackChain` that powers lap-time tools (`f1_get_lap_times`, `f1_tyre_degradation`, `f1_undercut_window`, `f1_head_to_head_pace`, `f1_predict_pit_strategy`).

## Resolution order

`openf1` → `fastf1_local`

| Adapter | Enabled by default |
| :--- | :--- |
| [[openf1]] | Yes for historical data; live access needs paid OpenF1 auth (not wired) |
| [[fastf1]] | Yes if `fastf1` package installed (`pip install sportiq-mcp[f1]`) |

## TTLs

- Fresh: 24h
- Stale ceiling: 7d

Keyless OpenF1 serves completed sessions only (live auth is not wired), and a completed session's
laps and stints never change, so they use the completed-session class from
`.claude/rules/caching-policy.md` (D18, 2026-10-22; previously 10s / 60s).

## Cache key

`sportiq:f1:laps:{session_key}:{driver_number_or_none}`
