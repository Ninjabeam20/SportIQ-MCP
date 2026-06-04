---
title: cross_sport_build_accumulator
type: tool
tags: [football, cricket, accumulator, cross-sport]
sources: []
last_updated: 2026-06-04
related: [[football-build-accumulator]], [[parlay-builder]]
---

# cross_sport_build_accumulator

Builds a multi-leg accumulator bet by combining value picks from both football and cricket, selecting the highest-edge legs across sports up to the requested count.

## Args

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `legs` | int | 3 | Total legs across both sports (2–8). |
| `min_edge` | float | 0.05 | Minimum edge per leg (0, 1) exclusive. |

## Return shape

```json
{
  "data": {
    "legs": [{"match_id": "football:123", "sport": "football", "outcome": "home", ...}, ...],
    "legs_used": 3,
    "combined_odds": 6.84,
    "combined_model_prob": 0.216,
    "combined_edge": 0.07,
    "risk_flag": false,
    "independence_warning": "..."
  },
  "meta": {
    "source": "derived",
    "estimated": true,
    "sports_available": ["football", "cricket"],
    "is_stale": false,
    "note": "cricket picks unavailable"
  }
}
```

## Failure modes

- `INVALID_INPUT` — `legs` outside 2–8 or `min_edge` outside (0, 1).
- `ALL_SOURCES_FAILED` — both football and cricket value-bet sources returned errors or exceptions.
- One sport failing is non-fatal: the accumulator is built from the remaining sport's picks, and `meta.note` records the failure.

## Implementation notes

- `normalise_pick` in `core/parlay.py` prefixes `match_id` with `sport:` (e.g. `football:123`) so the dedup step in `build_accumulator` never conflates the same raw ID across sports.
- Both sport fetches run concurrently via `asyncio.gather(..., return_exceptions=True)`.
