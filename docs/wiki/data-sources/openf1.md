---
title: OpenF1
type: data-source
tags: [f1, live-telemetry, laps, weather, sessions, drivers, stints]
sources: []
last_updated: 2026-05-28
related: [[f1-sessions-chain]], [[f1-laps-chain]], [[f1-stints-chain]], [[f1-weather-chain]], [[f1-drivers-chain]]
---

# OpenF1

Free public F1 telemetry API. No credentials required. Primary adapter for all F1 live-data chains.

## Base URL

`https://api.openf1.org/v1`

## Credentials

None. No API key required.

## Free-tier limits

None published. Cache aggressively; latency is the main constraint.

## Endpoints used

| Endpoint | Tool | Chain |
| :--- | :--- | :--- |
| `/sessions` | `f1_get_sessions` | [[f1-sessions-chain]] |
| `/drivers` | `f1_get_drivers`, `f1_get_race_results` | [[f1-drivers-chain]] |
| `/laps` | `f1_get_lap_times`, INTEL tools | [[f1-laps-chain]] |
| `/stints` | `f1_predict_pit_strategy` | [[f1-stints-chain]] |
| `/weather` | `f1_get_weather`, `f1_weather_strategy_impact` | [[f1-weather-chain]] |

## Adapter behavior

- Constructor never raises; `healthcheck()` does a lightweight ping.
- Returns empty lists for sessions/laps outside the available data range (2018–present).
