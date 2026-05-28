---
title: f1_head_to_head_pace
type: tool
tags: [f1, pace, head-to-head, intel]
sources: []
last_updated: 2026-05-28
related: [[f1-laps-chain]]
---

# f1_head_to_head_pace

Compares median lap-time pace between two drivers in the same session on matching compounds.

## Signature

```python
async def f1_head_to_head_pace(session_key: int, driver_a: int, driver_b: int) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`).
- `driver_a` — Driver number of the first driver.
- `driver_b` — Driver number of the second driver.

## Success response

```json
{
  "data": {
    "driver_a": {"driver_number": 1, "median_lap_s": 90.12},
    "driver_b": {"driver_number": 11, "median_lap_s": 90.45},
    "delta_s": -0.33,
    "faster_driver": 1
  },
  "meta": {"source": "openf1", "is_stale": false}
}
```

`delta_s` is `driver_a − driver_b`. Negative means driver_a is faster.

## Chain

[[f1-laps-chain]]
