---
title: football-data.org
type: data-source
tags: [football, fixtures, standings, scorers]
sources: []
last_updated: 2026-05-29
related: [[football-fixtures-chain]], [[football-standings-chain]], [[football-scorers-chain]], [[api-football]]
---

# football-data.org

Free fallback source (v4) for World Cup fixtures, standings and scorers. Token-optional.

## Base URL
`https://api.football-data.org/v4`

## Credentials
`FOOTBALLDATA_KEY` (header `X-Auth-Token`) is **optional** — the public tier works without it. The constructor never raises on a missing token.

## Free-tier limits
10 req/min, 100/day (`football_data_org` budget: per_minute=10, per_day=100).

## Endpoints used
| Endpoint | Common shape |
| :-- | :-- |
| `/competitions/WC/matches` | `{"fixtures": [...]}` |
| `/competitions/WC/standings` | `{"standings": [...]}` |
| `/competitions/WC/scorers` | `{"scorers": [...]}` |
| `/teams/{id}` | `{"team_stats": {...}}` |

Outputs are normalised to match [[api-football]] so it is a drop-in chain fallback.
