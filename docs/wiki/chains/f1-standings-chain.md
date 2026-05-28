---
title: F1 Standings Chain
type: chain
tags: [f1, standings]
sources: []
last_updated: 2026-05-28
related: [[jolpica]], [[fastf1]], [[f1-get-standings]]
---

# F1 Standings Chain

`FallbackChain` that powers `f1_get_standings`.

## Resolution order

`jolpica` → `fastf1_local`

| Adapter | Enabled by default |
| :--- | :--- |
| [[jolpica]] | Yes — no credentials required |
| [[fastf1]] | Yes if `fastf1` package installed (`pip install sportiq-mcp[f1]`) |

## TTLs

- Fresh: 24h
- Stale ceiling: 7d

## Cache key

`sportiq:f1:standings:{year}`
