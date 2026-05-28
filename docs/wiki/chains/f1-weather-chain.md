---
title: F1 Weather Chain
type: chain
tags: [f1, weather]
sources: []
last_updated: 2026-05-28
related: [[openf1]], [[f1-get-weather]], [[f1-weather-strategy-impact]], [[f1-predict-pit-strategy]]
---

# F1 Weather Chain

`FallbackChain` that powers `f1_get_weather`, `f1_weather_strategy_impact`, and rainfall detection in `f1_predict_pit_strategy`.

## Resolution order

`openf1`

| Adapter | Enabled by default |
| :--- | :--- |
| [[openf1]] | Yes — no credentials required |

## TTLs

- Fresh: 10min
- Stale ceiling: 24h

## Cache key

`sportiq:f1:weather:{session_key}`
