---
title: Cricket Odds Chain
type: chain
tags: [cricket, odds]
sources: []
last_updated: 2026-05-29
related: [[the-odds-api]], [[cricket-get-live-odds]]
---

# Cricket Odds Chain

`FallbackChain` powering `cricket_get_live_odds` — live IPL bookmaker h2h odds.

## Resolution order
the-odds-api (only source) → stale cache

| Adapter | Enabled by default |
| :-- | :-- |
| [[the-odds-api]] | Yes — when THEODDS_KEY set |

## TTLs
- Fresh: 5min (live ceiling)
- Stale ceiling: 24h (flagged)

## Cache key
`sportiq:cricket:odds:ipl` (sport-wide; the tool applies any team filter, so no args in the key)
