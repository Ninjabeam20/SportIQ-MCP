---
title: RapidAPI Cricbuzz
type: data-source
tags: [cricket, live-scores, fixtures, standings, player-stats, paid, opt-in]
sources: []
last_updated: 2026-09-25
related: [[cricket-live-score-chain]], [[cricket-scorecard-chain]], [[cricket-fixtures-chain]], [[cricket-standings-chain]], [[cricket-player-stats-chain]], [[0007-cricket-fallback-strategy]]
---

# RapidAPI Cricbuzz

Licensed Cricbuzz data mirror via RapidAPI (`cricbuzz-cricket.p.rapidapi.com`). It is the credential-gated escape hatch when free sources fail; plan prices and quotas depend on the operator's RapidAPI subscription.

## Credentials

Set `RAPIDAPI_KEY`. Without a key the adapter raises `MissingCredentialsError` and is skipped.

## Endpoints used

| Endpoint | Chain |
| :--- | :--- |
| `/matches/v1/live` | [[cricket-live-score-chain]] |
| `/mcenter/v1/{match_id}/scard` | [[cricket-scorecard-chain]] |
| `/matches/v1/upcoming` | [[cricket-fixtures-chain]] |
| `/series/v1/{id}/points-table` | [[cricket-standings-chain]] |
| `/stats/v1/player/{id}/career` | [[cricket-player-stats-chain]] |

## Adapter behavior

- Constructor never raises; `healthcheck()` returns `True` iff `RAPIDAPI_KEY` is set.
- Response shape differs from CricAPI: `typeMatches[].seriesMatches[].seriesAdWrapper.matches[]`.
- Adapter flattens this to `{"matches": [matchInfo, ...]}` matching the chain's output contract.

## Test fixtures

`tests/fixtures/rapidapi/live_matches.json` — from RapidAPI's public sample-response tab.
`tests/fixtures/rapidapi/scorecard.json` — synthetic shape representative of the `/mcenter/v1/{id}/scard` response.
`tests/fixtures/rapidapi/player_career.json` — synthetic shape representative of the `/stats/v1/player/{id}/career` response (per-format `values` rows: Test, ODI, T20I, IPL).
