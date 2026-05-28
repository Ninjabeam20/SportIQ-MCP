---
title: F1 Sessions Chain
type: chain
tags: [f1, sessions]
sources: []
last_updated: 2026-05-28
related: [[openf1]], [[jolpica]], [[f1-get-sessions]]
---

# F1 Sessions Chain

`FallbackChain` that powers `f1_get_sessions`.

## Resolution order

`openf1` → `jolpica`

| Adapter | Enabled by default |
| :--- | :--- |
| [[openf1]] | Yes — no credentials required |
| [[jolpica]] | Yes — no credentials required |

## TTLs

- Fresh: 6h
- Stale ceiling: 24h

## Cache key

`sportiq:f1:sessions:{year}:{country_or_none}`
