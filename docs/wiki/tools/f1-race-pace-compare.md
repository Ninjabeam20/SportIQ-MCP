---
title: f1_race_pace_compare
type: tool
tags: [f1, race-pace, strategy]
sources: []
last_updated: 2026-06-04
related: [[race-pace]], [[f1-tyre-degradation]]
---

# f1_race_pace_compare

Compares race-pace and tyre-degradation performance between two F1 drivers in the same session by fitting a per-compound linear degradation model for each driver.

## Parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `session_key` | int | OpenF1 session identifier |
| `driver_a` | int | First driver's race number |
| `driver_b` | int | Second driver's race number |

## Response

```json
{
  "data": {
    "driver_a": 1,
    "driver_b": 44,
    "by_compound": [
      {
        "compound": "MEDIUM",
        "intercept_a": 80.5,
        "intercept_b": 81.2,
        "slope_a": 0.08,
        "slope_b": 0.12,
        "pace_delta_s": -0.7,
        "faster_driver": 1,
        "sample_count_a": 12,
        "sample_count_b": 10
      }
    ],
    "overall_faster": 1,
    "compounds_compared": 1
  },
  "meta": {
    "source": "openf1",
    "estimated": true,
    "is_stale": false
  }
}
```

`pace_delta_s` = intercept_a − intercept_b; negative means driver_a is faster on fresh tyres.

`overall_faster` is the driver with more compound-wins; `null` if tied.

## Data sources

- Laps: `f1_laps_chain` (openf1 → fastf1_local)
- Stints: `f1_stints_chain` (openf1) — best-effort; outage degrades quality but does not fail the call

## Error codes

| Code | When |
| :--- | :--- |
| `INVALID_INPUT` | `session_key ≤ 0`, either driver ≤ 0, or `driver_a == driver_b` |
| `ALL_SOURCES_FAILED` | Lap data unavailable for one or both drivers |

## Notes

- Uses `compare_race_pace()` from [[race-pace]] model
- Compounds with `sample_count == 0` for either driver are skipped
- `meta.estimated: true` always — this is a model fit, not official timing data
