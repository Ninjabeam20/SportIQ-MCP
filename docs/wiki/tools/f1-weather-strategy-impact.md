---
title: f1_weather_strategy_impact
type: tool
tags: [f1, weather, strategy, intel]
sources: []
last_updated: 2026-09-11
related: [[f1-weather-chain]]
---

# f1_weather_strategy_impact

Analyzes session weather data and returns a compound recommendation based on rainfall and track temperature.

## Signature

```python
async def f1_weather_strategy_impact(session_key: int) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`).

## Success response

```json
{
  "data": {
    "has_rain": false,
    "avg_track_temp_c": 42.1,
    "compound_recommendation": "MEDIUM",
    "recommendation": "Nominal conditions — MEDIUM is the baseline choice."
  },
  "meta": {"source": "openf1", "is_stale": false, "estimated": true}
}
```

When `has_rain` is true, `compound_recommendation` is `INTER`.

## Chain

[[f1-weather-chain]]
