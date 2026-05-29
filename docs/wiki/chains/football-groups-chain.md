---
title: Football Groups Chain
type: chain
tags: [football]
sources: []
last_updated: 2026-05-29
related: [[static-seed]], [[football-get-groups]], [[bracket-sim]]
---

# Football Groups Chain

`FallbackChain` powering football tools.

## Resolution order
static-seed

| Adapter | Enabled by default |
| :-- | :-- |
| [[static-seed]] | Yes — bundled JSON |

## TTLs
- Fresh: ~1y (static seed)
- Stale ceiling: ~1y

## Cache key
`sportiq:football:groups:wc2026`

The terminator returns the canonical 2026 draw **plus** Elo ratings; all INTEL tools read it.
