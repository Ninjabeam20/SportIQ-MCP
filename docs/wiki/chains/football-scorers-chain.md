---
title: Football Scorers Chain
type: chain
tags: [football]
sources: []
last_updated: 2026-05-29
related: [[api-football]], [[football-data-org]], [[football-get-top-scorers]]
---

# Football Scorers Chain

`FallbackChain` powering football tools.

## Resolution order
api-football -> football-data-org

| Adapter | Enabled by default |
| :-- | :-- |
| [[api-football]] | Yes — when APIFOOTBALL_KEY set |
| [[football-data-org]] | Yes — token optional |

## TTLs
- Fresh: 24h
- Stale ceiling: 7d

## Cache key
`sportiq:football:scorers:wc2026`

