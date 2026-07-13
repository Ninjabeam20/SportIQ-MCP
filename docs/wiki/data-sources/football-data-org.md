---
title: football-data.org
type: data-source
tags: [football, fixtures, standings, scorers]
sources: []
last_updated: 2026-07-14
related: [[football-fixtures-chain]], [[football-standings-chain]], [[football-scorers-chain]], [[api-football]], [[openfootball]]
---

# football-data.org

Free fallback source (v4) for World Cup fixtures, standings and scorers. The free tier includes the
World Cup, but a (free) token is required to reach it.

## Base URL
`https://api.football-data.org/v4`

## Credentials
`FOOTBALLDATA_KEY` (header `X-Auth-Token`) is **required for the World Cup competition** — token-less
`/competitions/WC/matches` returns **HTTP 403**. The token is free (register at football-data.org). The
constructor still never raises on a missing token: without one the adapter simply 403s and the chain
walks past it to the keyless [[openfootball]] / [[static-seed]] fallbacks.

## Free-tier limits
10 req/min, 100/day (`football_data_org` budget: per_minute=10, per_day=100).

## Endpoints used
| Endpoint | Common shape |
| :-- | :-- |
| `/competitions/WC/matches` | `{"fixtures": [...]}` |
| `/competitions/WC/standings` | `{"standings": [...]}` |
| `/competitions/WC/scorers` | `{"scorers": [...]}` |
| `/teams/{id}` | `{"team_stats": {...}}` |

Outputs are normalised to match [[api-football]] so it is a drop-in chain fallback. Fixture `id`
becomes `match_id`, `stage` is preserved, and `score.winner` maps `HOME_TEAM` / `AWAY_TEAM` to the
winning team name (including level full-time scores decided after regulation).
