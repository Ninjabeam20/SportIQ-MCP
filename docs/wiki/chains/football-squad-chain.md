---
title: Football Squad Chain
type: chain
tags: [football]
sources: []
last_updated: 2026-05-29
related: [[api-football]], [[static-seed]], [[football-get-squad]]
---

# Football Squad Chain

`FallbackChain` powering football tools.

## Resolution order
api-football -> static-seed

| Adapter | Enabled by default |
| :-- | :-- |
| [[api-football]] | Yes — when APIFOOTBALL_KEY set |
| [[static-seed]] | Yes — bundled JSON |

## TTLs
- Fresh: 12h
- Stale ceiling: 3d

## Cache key
`sportiq:football:squad:{team}`

No rosters are bundled yet — the static terminator returns an empty-but-valid squad (follow-up).
