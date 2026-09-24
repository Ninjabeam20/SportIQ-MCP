---
title: Football Team Stats Chain
type: chain
tags: [football]
sources: []
last_updated: 2026-09-25
related: [[api-football]], [[football-data-org]], [[football-get-match-stats]]
---

# Football Team Stats Chain

`FallbackChain` powering football tools.

## Resolution order
api-football -> football-data-org (registered, but its team-stats adapter currently returns `NotFoundError` because `/teams/{id}` is a profile endpoint in a different ID space)

| Adapter | Enabled by default |
| :-- | :-- |
| [[api-football]] | Yes — when APIFOOTBALL_KEY set |
| [[football-data-org]] | Registered; requires `FOOTBALLDATA_KEY`, but cannot serve team stats with the current mapping |

## TTLs
- Fresh: 24h
- Stale ceiling: 7d

## Cache key
`sportiq:football:team_stats:{team}`
