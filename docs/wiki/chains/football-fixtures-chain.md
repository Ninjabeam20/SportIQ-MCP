---
title: Football Fixtures Chain
type: chain
tags: [football]
sources: []
last_updated: 2026-07-14
related: [[api-football]], [[football-data-org]], [[openfootball]], [[static-seed]], [[football-get-fixtures]]
---

# Football Fixtures Chain

`FallbackChain` powering football tools.

## Resolution order
api-football -> football-data-org -> openfootball -> static-seed

| Adapter | Enabled by default |
| :-- | :-- |
| [[api-football]] | Yes — when APIFOOTBALL_KEY set |
| [[football-data-org]] | Yes — but needs a free token (WC 403s token-less) |
| [[openfootball]] | Yes — keyless; real results (hand-updated ~daily) |
| [[static-seed]] | Yes — bundled JSON; scores-less schedule terminator |

## TTLs
- Fresh: 30min (the chain now carries live results, not a static schedule)
- Stale ceiling: 24h

## Cache key
`sportiq:football:fixtures:wc2026`

## Normalized fixture contract

Every adapter returns the existing home/away/date/status/score fields plus `match_id`, `stage`,
and `winner`. Network adapters preserve native IDs when available; the static seed uses a stable
group/pair ID. Conditioning uses identity + stage so group and knockout rematches cannot collide.
