---
title: f1_weather_strategy_impact
type: tool
tags: [f1, weather, strategy, intel]
sources: []
last_updated: 2026-05-28
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
    "rainfall_detected": false,
    "avg_track_temp_c": 42.1,
    "recommended_compound": "MEDIUM",
    "rationale": "Dry track, moderate temperature — MEDIUM offers best balance of pace and life."
  },
  "meta": {"source": "openf1", "is_stale": false}
}
```

When `rainfall_detected` is true, `recommended_compound` is `INTER` or `WET`.

## Chain

[[f1-weather-chain]]
