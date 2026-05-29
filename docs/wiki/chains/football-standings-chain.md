---
title: Football Standings Chain
type: chain
tags: [football]
sources: []
last_updated: 2026-05-29
related: [[api-football]], [[football-data-org]], [[football-get-standings]]
---

# Football Standings Chain

`FallbackChain` powering football tools.

## Resolution order
api-football -> football-data-org

| Adapter | Enabled by default |
| :-- | :-- |
| [[api-football]] | Yes — when APIFOOTBALL_KEY set |
| [[football-data-org]] | Yes — token optional |

## TTLs
- Fresh: 10min
- Stale ceiling: 1h

## Cache key
`sportiq:football:standings:wc2026`

