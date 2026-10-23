---
title: Football Fixtures Chain
type: chain
tags: [football]
sources: [src/sportiq/football/chains.py, .claude/rules/caching-policy.md]
last_updated: 2026-10-22
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
- Fresh: 6h — the static schedule class. The WC 2026 final was played 2026-07-19, so results no longer
  change; the 30min live-tournament class applied only while the tournament was in progress (D18,
  `.claude/rules/caching-policy.md`).
- Stale ceiling: 24h

## Cache key
`sportiq:football:fixtures:wc2026`

## Normalized fixture contract

Every adapter returns the existing home/away/date/status/score fields plus `match_id`, `stage`,
and `winner` (a team **name**). [[openfootball]] also carries regulation and penalty scores, so
extra-time and shootout ties are decided. Network adapters preserve native IDs when available; the static seed uses a stable
group/pair ID. Conditioning uses identity + stage so group and knockout rematches cannot collide.
