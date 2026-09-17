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
- Fresh: ~1y (`31536000`s — static tournament draw seed)
- Stale ceiling: ~1y

### Rationale
The ~1-year TTL is intentional. The groups payload represents the static draw structure (12 groups of 4) and frozen pre-tournament baseline Elo ratings for FIFA World Cup 2026. This structure is immutable across the tournament and remains valid post-tournament as the canonical baseline. In-tournament dynamic conditioning (actual match scores, knockout progression, and live Elo nudges) is applied downstream in memory via `_maybe_nudge_single` and `results_state`, leaving the underlying seed cache invariant.

## Cache key
`sportiq:football:groups:wc2026`

The terminator returns the canonical 2026 draw **plus** Elo ratings; all INTEL tools read it.

