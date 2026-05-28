---
title: f1_get_race_results
type: tool
tags: [f1, race-results]
sources: []
last_updated: 2026-05-28
related: [[f1-drivers-chain]], [[openf1]]
---

# f1_get_race_results

Returns race results (finishing positions, points, fastest lap) for a given session.

## Signature

```python
async def f1_get_race_results(session_key: int) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`). Should point to a Race session.

## Success response

```json
{
  "data": {"results": [{"position": 1, "driver_number": 1, "full_name": "Max Verstappen", "points": 25, "status": "Finished"}]},
  "meta": {"source": "openf1", "is_stale": false}
}
```

## Chain

[[f1-drivers-chain]]
