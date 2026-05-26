---
title: Cricket Standings Chain
type: chain
tags: [cricket, standings, points-table]
sources: []
last_updated: 2026-05-26
related: [[cricapi]], [[rapidapi-cricbuzz]]
---

# Cricket Standings Chain

`FallbackChain` that powers `cricket_get_points_table`.

## Resolution order

`cricapi` → `rapidapi_cricbuzz`

## TTLs

- Fresh: 10min
- Stale ceiling: 1h

## Cache key

`sportiq:cricket:standings:{series_id}`
