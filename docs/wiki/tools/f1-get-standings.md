---
title: f1_get_standings
type: tool
tags: [f1, standings]
sources: []
last_updated: 2026-10-22
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
    "season": 2026,
    "round": 17,
    "drivers": [{"position": 1, "driver_number": 12, "code": "ANT", "name": "Andrea Kimi Antonelli", "team": "Mercedes", "points": 325.0, "wins": 7}],
    "constructors": [{"position": 1, "team": "Mercedes", "points": 561.0, "wins": 10}]
  },
  "meta": {"source": "jolpica", "is_stale": false}
}
```

Jolpica (primary) and the FastF1 fallback return this same shape. FastF1
sums per-race points into season totals and omits sprint points. Illustrative
values; driver numbers change by season.

## Chain

[[f1-standings-chain]]
