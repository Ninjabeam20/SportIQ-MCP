---
title: Cricket Player Stats Chain
type: chain
tags: [cricket, player-stats, t20]
sources: []
last_updated: 2026-05-28
related: [[cricapi]], [[rapidapi-cricbuzz]], [[cricket-player-form-index]], [[form-index]]
---

# Cricket Player Stats Chain

`FallbackChain` powering [[cricket-player-form-index]]. Recreated in Phase 2 with new resolution order after CricSheet was dropped (ADR-0007 amendment, commit 9a37236).

## Resolution order

`cricapi_player_info` → `rapidapi_player_stats` → stale cache

CricAPI is the free primary (budgeted at 100 req/day, shared across endpoints). RapidAPI Cricbuzz is the paid escape hatch — different response shape, [[cricket-player-form-index]] handles both via `_t20_career_numbers()`.

## TTLs

- Fresh: 24h (`86_400`s)
- Stale ceiling: 7d (`604_800`s)

Player stats change slowly; aggressive caching is correct.

## Cache key

`sportiq:cricket:player_stats:{player_id}`

Per-player keying lets one popular query (e.g. Kohli's ID) prime the cache without affecting unrelated players.
