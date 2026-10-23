---
title: API-Football
type: data-source
tags: [football, fixtures, standings, squad, scorers]
sources: [src/sportiq/football/adapters/api_football.py]
last_updated: 2026-10-22
related: [[football-fixtures-chain]], [[football-standings-chain]], [[football-squad-chain]], [[football-scorers-chain]], [[football-team-stats-chain]]
---

# API-Football

Primary network source for World Cup 2026 fixtures, standings, team stats, squads and top scorers.

## Base URL
`https://v3.football.api-sports.io`

## Credentials
`APIFOOTBALL_KEY` (header `x-apisports-key`). Missing key -> `MissingCredentialsError`; the chain walks past.

## Free-tier limits
100 req/day, shared across endpoints (one `api_football` budget). See `.claude/rules/api-budgets.md`.

## Endpoints used
| Endpoint | Tool | Chain |
| :-- | :-- | :-- |
| `/fixtures` | `football_get_fixtures` | [[football-fixtures-chain]] |
| `/standings` | `football_get_standings` | [[football-standings-chain]] |
| `/teams/statistics` | `football_get_match_stats` | [[football-team-stats-chain]] |
| `/players/squads` | `football_get_squad` | [[football-squad-chain]] |
| `/players/topscorers` | `football_get_top_scorers` | [[football-scorers-chain]] |

Each adapter normalises the provider's `{"response": [...]}` envelope into the common per-chain
shape. Fixtures preserve `fixture.id` as `match_id`, `league.round` as `stage`, and the name whose
`teams.*.winner` flag is true as `winner`; this supports rematches and shootouts in live conditioning.

## Misses never cost quota or poison the cache
- An empty `response` (the free plan returns one silently for seasons it does not cover, e.g. WC 2026)
  raises `NotFoundError`, so the chain walks on instead of caching emptiness.
- `/players/squads` takes an integer team id. A FIFA code (`"ARG"`) is a guaranteed miss, so the squad
  adapter raises `NotFoundError` **before** any request — no daily quota is spent on it. With the bundled
  football squad seed removed (see [[football-squad-chain]]), a squad needs `APIFOOTBALL_KEY` and a numeric id.
- Fixture `status` uses api-football short codes (`FT`/`AET`/`PEN`), not `FINISHED`; [[results-state]]
  gates finished-detection on the status set.
