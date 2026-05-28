---
title: f1_get_drivers
type: tool
tags: [f1, drivers]
sources: []
last_updated: 2026-05-28
related: [[f1-drivers-chain]], [[openf1]]
---

# f1_get_drivers

Returns the driver list for a given F1 session.

## Signature

```python
async def f1_get_drivers(session_key: int) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`).

## Success response

```json
{
  "data": {"drivers": [{"driver_number": 1, "full_name": "Max Verstappen", "team_name": "Red Bull Racing", "country_code": "NED"}]},
  "meta": {"source": "openf1", "is_stale": false}
}
```

## Chain

[[f1-drivers-chain]]
