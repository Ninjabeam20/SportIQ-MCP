---
title: Jolpica
type: data-source
tags: [f1, standings, race-results, historical]
sources: []
last_updated: 2026-09-25
related: [[f1-results-chain]], [[f1-standings-chain]]
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
| `/f1/{year}/driverStandings.json` | `f1_get_standings` | [[f1-standings-chain]] |
| `/f1/{year}/constructorStandings.json` | `f1_get_standings` | [[f1-standings-chain]] |
| `/f1/{year}/{round}/results.json` | `f1_get_race_results` | [[f1-results-chain]] |

## Adapter behavior

- Constructor never raises; `healthcheck()` returns `True` (no key needed).
- Provides historical snapshot data per season; does not provide live timing.
