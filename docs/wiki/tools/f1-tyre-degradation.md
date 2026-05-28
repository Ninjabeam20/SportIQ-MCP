---
title: f1_tyre_degradation
type: tool
tags: [f1, tyre, degradation, intel]
sources: []
last_updated: 2026-05-28
related: [[f1-laps-chain]], [[tyre-degradation-model]]
---

# f1_tyre_degradation

Fits a linear tyre-degradation model (lap_time = intercept + slope × tyre_age) for a driver and compound in a session.

## Signature

```python
async def f1_tyre_degradation(session_key: int, driver_number: int, compound: str) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`).
- `driver_number` — Driver number (e.g. 1 for Verstappen).
- `compound` — Tyre compound: `SOFT`, `MEDIUM`, `HARD`, `INTER`, or `WET`.

## Success response

```json
{
  "data": {
    "compound": "MEDIUM",
    "intercept": 90.2,
    "slope": 0.048,
    "residual_std": 0.31,
    "sample_count": 18
  },
  "meta": {"source": "openf1", "is_stale": false}
}
```

`slope` is in seconds per lap — positive means the tyre is degrading.

## Chain

[[f1-laps-chain]]
