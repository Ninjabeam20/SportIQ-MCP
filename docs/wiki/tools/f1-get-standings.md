---
title: f1_get_standings
type: tool
tags: [f1, standings]
sources: []
last_updated: 2026-09-02
related: [[f1-standings-chain]], [[jolpica]]
---

# f1_get_standings

Returns driver and constructor championship standings for a given F1 season.
Use this for "who is leading / who will win the F1 championship this year" —
there is no F1 title Monte Carlo; current points are the answer.

## Signature

```python
async def f1_get_standings(year: int) -> dict
```

## Args
- `year` — Championship year (e.g. 2026).

## Success response

```json
{
  "data": {
    "drivers": [{"position": 1, "driver": "Max Verstappen", "points": 575}],
    "constructors": [{"position": 1, "constructor": "Red Bull", "points": 860}]
  },
  "meta": {"source": "jolpica", "is_stale": false}
}
```

## Chain

[[f1-standings-chain]]
