---
title: Jolpica
type: data-source
tags: [f1, standings, race-results, historical]
sources: []
last_updated: 2026-05-28
related: [[f1-sessions-chain]], [[f1-standings-chain]]
---

# Jolpica

Free public Ergast successor API for historical F1 championship data. No credentials required.

## Base URL

`https://api.jolpi.ca/ergast`

## Credentials

None. No API key required.

## Free-tier limits

None published. Cache aggressively; historical data changes infrequently.

## Endpoints used

| Endpoint | Tool | Chain |
| :--- | :--- | :--- |
| `/{year}/driverStandings` | `f1_get_standings` | [[f1-standings-chain]] |
| `/{year}/constructorStandings` | `f1_get_standings` | [[f1-standings-chain]] |
| `/{year}/results` | fallback for `f1_get_sessions` | [[f1-sessions-chain]] |

## Adapter behavior

- Constructor never raises; `healthcheck()` returns `True` (no key needed).
- Provides historical snapshot data per season; does not provide live timing.
