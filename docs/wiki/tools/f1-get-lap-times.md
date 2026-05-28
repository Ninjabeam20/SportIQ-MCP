---
title: f1_get_lap_times
type: tool
tags: [f1, laps]
sources: []
last_updated: 2026-05-28
related: [[f1-laps-chain]], [[openf1]]
---

# f1_get_lap_times

Returns per-driver lap times with tyre compound data for a session.

## Signature

```python
async def f1_get_lap_times(session_key: int, driver_number: int | None = None) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`).
- `driver_number` — Optional driver number filter. If omitted returns all drivers.

## Success response

```json
{
  "data": {"laps": [{"driver_number": 1, "lap_number": 10, "lap_duration": 90.123, "compound": "SOFT"}]},
  "meta": {"source": "openf1", "is_stale": false}
}
```

## Chain

[[f1-laps-chain]]
