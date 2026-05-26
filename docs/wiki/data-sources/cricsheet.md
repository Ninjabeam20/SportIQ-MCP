---
title: CricSheet
type: data-source
tags: [cricket, player-stats, squad, historical]
sources: []
last_updated: 2026-05-26
related: [[cricket-player-stats-chain]], [[cricket-squad-chain]]
---

# CricSheet

Free, public-domain cricket data from [cricsheet.org](https://cricsheet.org). No API key required. Always enabled. Used for player career stats and squad lookups where historical accuracy matters more than latency.

## Limitations

Data is hours-stale for completed matches and not useful for live scores. The [[cricket-live-score-chain]] does not include this adapter; it appears only in [[cricket-player-stats-chain]] and [[cricket-squad-chain]].

## Endpoints used

| Endpoint | Purpose |
| :--- | :--- |
| `/register/people.json` | Player registry — name, unique name, teams |

## Adapter behavior

- Always enabled (no credential check).
- `healthcheck()` fetches `people.json` and verifies it is a non-empty list.
- Player-name filtering is substring-match, case-insensitive.
- Team filtering matches any entry in the player's `teams` array.

## Test fixtures

`tests/fixtures/cricsheet/player_stats_sample.json` — 2-record subset.
`tests/fixtures/cricsheet/squad_sample.json` — 3-record subset including Mumbai Indians players.
