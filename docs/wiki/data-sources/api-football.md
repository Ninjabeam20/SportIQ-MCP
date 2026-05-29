---
title: API-Football
type: data-source
tags: [football, fixtures, standings, squad, scorers]
sources: []
last_updated: 2026-05-29
related: [[football-fixtures-chain]], [[football-standings-chain]], [[football-squad-chain]], [[football-scorers-chain]], [[football-team-stats-chain]]
---

# API-Football

Primary network source for World Cup 2026 fixtures, standings, team stats, squads and top scorers.

## Base URL
`https://v3.football.api-sports.io`

## Credentials
`APIFOOTBALL_KEY` (header `x-apisports-key`). Missing key -> `MissingCredentialsError`; the chain walks past.

## Free-tier limits
100 req/day, shared across endpoints (one `api_football` budget). See [[../../../.claude/rules/api-budgets]].

## Endpoints used
| Endpoint | Tool | Chain |
| :-- | :-- | :-- |
| `/fixtures` | `football_get_fixtures` | [[football-fixtures-chain]] |
| `/standings` | `football_get_standings` | [[football-standings-chain]] |
| `/teams/statistics` | `football_get_match_stats` | [[football-team-stats-chain]] |
| `/players/squads` | `football_get_squad` | [[football-squad-chain]] |
| `/players/topscorers` | `football_get_top_scorers` | [[football-scorers-chain]] |

Each adapter normalises the provider's `{"response": [...]}` envelope into the common per-chain shape.
