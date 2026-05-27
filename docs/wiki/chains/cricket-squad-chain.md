---
title: Cricket Squad Chain
type: chain
tags: [cricket, squad, roster]
sources: []
last_updated: 2026-05-27
related: [[cricapi]], [[static-seed]]
---

# Cricket Squad Chain

`FallbackChain` that powers `cricket_get_squad`. Always terminates in `static_seed` so there is always a last-resort response.

## Resolution order

`cricapi` → `static_seed`

`static_seed` is always enabled and serves IPL 2026 rosters from `src/sportiq/cricket/data/squads.json`.

## TTLs

- Fresh: 12h
- Stale ceiling: 3d

## Cache key

`sportiq:cricket:squad:{team|all}:{series_id|none}`
