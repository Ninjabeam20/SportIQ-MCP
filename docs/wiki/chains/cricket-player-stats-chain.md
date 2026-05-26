---
title: Cricket Player Stats Chain
type: chain
tags: [cricket, player-stats]
sources: []
last_updated: 2026-05-26
related: [[cricsheet]], [[cricapi]]
---

# Cricket Player Stats Chain

`FallbackChain` for player career statistics. CricSheet is the primary (free, no key, redistributable). CricAPI is the fallback.

## Resolution order

`cricsheet` → `cricapi`

## TTLs

- Fresh: 24h
- Stale ceiling: 7d

## Cache key

`sportiq:cricket:player_stats:{player_name}`
