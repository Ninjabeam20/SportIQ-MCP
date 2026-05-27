---
title: Cricket Scorecard Chain
type: chain
tags: [cricket, scorecard, live-scores]
sources: []
last_updated: 2026-05-27
related: [[cricapi]], [[rapidapi-cricbuzz]]
---

# Cricket Scorecard Chain

`FallbackChain` that powers `cricket_get_scorecard`. Isolated from [[cricket-live-score-chain]] so per-match cache keys don't collide with the bulk live-matches response.

## Resolution order

`cricapi` → `rapidapi_cricbuzz`

| Adapter | Endpoint | Enabled by default |
| :--- | :--- | :--- |
| [[cricapi]] | `/v1/match_scorecard` | Yes, if `CRICAPI_KEY` set |
| [[rapidapi-cricbuzz]] | `/mcenter/v1/{match_id}/scard` | No — `RAPIDAPI_KEY` set |

## TTLs

- Fresh: 30s
- Stale ceiling: 5min

## Cache key

`sportiq:cricket:scorecard:{match_id}` — keyed per match so concurrent lookups don't collide.
