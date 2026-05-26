---
title: Cricket Fixtures Chain
type: chain
tags: [cricket, fixtures, schedule]
sources: []
last_updated: 2026-05-26
related: [[cricapi]], [[ndtv-sports-scraper]], [[rapidapi-cricbuzz]]
---

# Cricket Fixtures Chain

`FallbackChain` that powers `cricket_get_schedule`.

## Resolution order

`cricapi` → `ndtv_sports_scraper` → `rapidapi_cricbuzz`

## TTLs

- Fresh: 6h
- Stale ceiling: 24h

## Cache key

`sportiq:cricket:fixtures:{series_id|all}`
