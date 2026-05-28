---
title: f1_get_weather
type: tool
tags: [f1, weather]
sources: []
last_updated: 2026-05-28
related: [[f1-weather-chain]], [[openf1]]
---

# f1_get_weather

Returns track weather data (temperature, rainfall, wind speed) for a session.

## Signature

```python
async def f1_get_weather(session_key: int) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`).

## Success response

```json
{
  "data": {"weather": [{"date": "...", "air_temperature": 28.3, "track_temperature": 42.1, "rainfall": false, "wind_speed": 2.1}]},
  "meta": {"source": "openf1", "is_stale": false}
}
```

## Chain

[[f1-weather-chain]]
