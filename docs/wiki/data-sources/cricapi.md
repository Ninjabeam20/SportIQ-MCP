---
title: CricAPI
type: data-source
tags: [cricket, live-scores, fixtures, standings, squad, player-stats]
sources: []
last_updated: 2026-05-28
related: [[cricket-live-score-chain]], [[cricket-scorecard-chain]], [[cricket-fixtures-chain]], [[cricket-standings-chain]], [[cricket-squad-chain]], [[cricket-player-stats-chain]]
---

# CricAPI

Free JSON API for live cricket scores, fixtures, standings, and squad rosters. Primary adapter for all four cricket RAW chains.

## Credentials

Set `CRICAPI_KEY` in the environment. The key is obtained from [cricapi.com](https://www.cricapi.com). Without a key the adapter raises `MissingCredentialsError` and the chain walks past it.

## Free-tier limits

100 requests/day. Hard cap — exhausting it kills live scores until midnight UTC reset. The rate limiter in `core/ratelimit.py` tracks daily usage. See [[api-budgets]].

## Endpoints used

| Endpoint | Tool | Chain |
| :--- | :--- | :--- |
| `/v1/currentMatches` | `cricket_get_live_matches` | [[cricket-live-score-chain]] |
| `/v1/match_scorecard` | `cricket_get_scorecard` | [[cricket-scorecard-chain]] |
| `/v1/matches` | `cricket_get_schedule` | [[cricket-fixtures-chain]] |
| `/v1/series_points_table` | `cricket_get_points_table` | [[cricket-standings-chain]] |
| `/v1/series_squad` | `cricket_get_squad` | [[cricket-squad-chain]] |
| `/v1/players_info` | `cricket_player_form_index` | [[cricket-player-stats-chain]] |
| `/v1/players` | (reserved) | [[cricket-player-stats-chain]] |

## Adapter behavior

- Constructor never raises; `healthcheck()` returns `False` when key is absent.
- `fetch()` raises `MissingCredentialsError` when key is absent (treated as adapter failure by the chain).
- Off-season: `/v1/currentMatches` returns `data: []`; adapter returns `{"matches": []}` — not an error.
