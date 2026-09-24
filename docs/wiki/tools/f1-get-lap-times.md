---
title: f1_get_lap_times
type: tool
tags: [f1, laps]
sources: []
last_updated: 2026-09-25
related: [[f1-laps-chain]], [[f1-stints-chain]], [[openf1]]
---

# f1_get_lap_times

Returns per-driver lap times for a session.

> OpenF1's `/laps` carries **no** `compound` or `tyre_life` — those live on `/stints`. To attribute laps to a compound, merge with [[f1-stints-chain]] (the INTEL tools do this via `annotate_laps_with_stints`).

## Signature

```python
async def f1_get_lap_times(session_key: int, driver_number: int, limit: int = 100, offset: int = 0) -> Envelope
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`).
- `driver_number` — Required driver number.
- `limit` / `offset` — Paginate the driver's laps.

## Success response

```json
{
  "data": {"laps": [{"driver_number": 1, "lap_number": 10, "lap_duration": 90.123, "is_pit_out_lap": false}]},
  "meta": {"source": "openf1", "is_stale": false}
}
```

## Chain

[[f1-laps-chain]]
