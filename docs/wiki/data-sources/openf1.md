---
title: OpenF1
type: data-source
tags: [f1, live-telemetry, laps, weather, sessions, drivers, stints]
sources: []
last_updated: 2026-09-25
related: [[f1-sessions-chain]], [[f1-laps-chain]], [[f1-stints-chain]], [[f1-weather-chain]], [[f1-drivers-chain]]
---

# OpenF1

OpenF1 supplies F1 telemetry. Historical sessions from 2023 onward are free and keyless; data during a live session requires paid authentication. It is the primary source for the F1 telemetry chains.

## Base URL

`https://api.openf1.org/v1`

## Credentials

No key is needed for historical sessions. [OpenF1's current access policy](https://openf1.org/docs/) requires a paid subscription for real-time data; this package does not implement OpenF1 authentication.

## Free-tier limits

The [community tier](https://openf1.org/) allows up to 3 requests/second and 30 requests/minute for historical data. Cached responses limit repeat requests.

## Endpoints used

| Endpoint | Tool | Chain |
| :--- | :--- | :--- |
| `/sessions` | `f1_get_sessions` | [[f1-sessions-chain]] |
| `/drivers` | `f1_get_drivers` | [[f1-drivers-chain]] |
| `/laps` | `f1_get_lap_times`, INTEL tools | [[f1-laps-chain]] |
| `/stints` | `f1_predict_pit_strategy` | [[f1-stints-chain]] |
| `/weather` | `f1_get_weather`, `f1_weather_strategy_impact` | [[f1-weather-chain]] |

## Adapter behavior

- Constructor never raises; `healthcheck()` returns `True` without a network ping.
- Empty sessions are valid for a year/country filter. Empty drivers, laps, or stints raise `NotFoundError` so the chain can try its fallback or return a structured miss.
