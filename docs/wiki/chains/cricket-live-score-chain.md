---
title: Cricket Live Score Chain
type: chain
tags: [cricket, live-scores]
sources: []
last_updated: 2026-05-26
related: [[cricapi]], [[ndtv-sports-scraper]], [[cricbuzz-scraper]], [[rapidapi-cricbuzz]]
---

# Cricket Live Score Chain

`FallbackChain` that powers `cricket_get_live_matches` and `cricket_get_scorecard`.

## Resolution order

`cricapi` → `ndtv_sports_scraper` → `cricbuzz_scraper` → `rapidapi_cricbuzz`

| Adapter | Enabled by default |
| :--- | :--- |
| [[cricapi]] | Yes, if `CRICAPI_KEY` set |
| [[ndtv-sports-scraper]] | No — `SPORTIQ_ENABLE_NDTV=1` |
| [[cricbuzz-scraper]] | No — `SPORTIQ_ENABLE_CRICBUZZ=1` |
| [[rapidapi-cricbuzz]] | No — `RAPIDAPI_KEY` set |

## TTLs

- Fresh: 30s
- Stale ceiling: 5min

## Cache key

`sportiq:cricket:live_score:all`
