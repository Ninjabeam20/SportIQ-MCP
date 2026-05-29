---
title: Football Odds Chain
type: chain
tags: [football, odds]
sources: []
last_updated: 2026-05-29
related: [[the-odds-api]], [[football-get-odds]]
---

# Football Odds Chain

`FallbackChain` powering `football_get_odds` — live World Cup 2026 bookmaker h2h odds.

## Resolution order
the-odds-api (only source) → stale cache

| Adapter | Enabled by default |
| :-- | :-- |
| [[the-odds-api]] | Yes — when THEODDS_KEY set |

## TTLs
- Fresh: 5min (live ceiling)
- Stale ceiling: 24h (flagged)

## Cache key
`sportiq:football:odds:wc2026` (sport-wide; the tool applies any team filter, so no args in the key)
