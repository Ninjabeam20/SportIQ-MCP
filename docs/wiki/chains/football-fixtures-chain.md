---
title: Football Fixtures Chain
type: chain
tags: [football]
sources: []
last_updated: 2026-05-29
related: [[api-football]], [[football-data-org]], [[static-seed]], [[football-get-fixtures]]
---

# Football Fixtures Chain

`FallbackChain` powering football tools.

## Resolution order
api-football -> football-data-org -> static-seed

| Adapter | Enabled by default |
| :-- | :-- |
| [[api-football]] | Yes — when APIFOOTBALL_KEY set |
| [[football-data-org]] | Yes — token optional |
| [[static-seed]] | Yes — bundled JSON |

## TTLs
- Fresh: 6h
- Stale ceiling: 24h

## Cache key
`sportiq:football:fixtures:wc2026`

