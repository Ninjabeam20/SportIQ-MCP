---
title: F1 Sessions Chain
type: chain
tags: [f1, sessions]
sources: []
last_updated: 2026-05-29
related: [[openf1]], [[f1-get-sessions]]
---

# F1 Sessions Chain

`FallbackChain` that powers `f1_get_sessions`.

## Resolution order

`openf1` (only source)

| Adapter | Enabled by default |
| :--- | :--- |
| [[openf1]] | Yes — no credentials required |

> Phase 3.1 (audit finding #2): [[jolpica]] was wired as a fallback here but its results adapter has a different call signature (requires `round`) and output shape (`results`, not `sessions`) — it raised `TypeError` on every attempt and was silently skipped. Removed; sessions is OpenF1-only. Jolpica now backs [[f1-results-chain]] instead.

## TTLs

- Fresh: 6h
- Stale ceiling: 24h

## Cache key

`sportiq:f1:sessions:{year}:{country_or_none}`
