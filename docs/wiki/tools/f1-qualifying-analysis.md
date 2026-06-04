---
title: f1_qualifying_analysis
type: tool
tags: [f1, qualifying, grid]
sources: []
last_updated: 2026-06-04
related: [[quali-analysis]], [[f1-tyre-degradation]], [[f1-head-to-head-pace]]
---

# f1_qualifying_analysis

Analyse a qualifying session: best lap per driver, gap to pole, and projected grid order.

## Args

| Arg | Type | Description |
|-----|------|-------------|
| `session_key` | `int` | OpenF1 session identifier (must be positive). |

## Returns

```json
{
  "data": {
    "grid": [
      {
        "position": 1,
        "driver_number": 1,
        "full_name": "Max Verstappen",
        "team_name": "Red Bull Racing",
        "best_lap_gap_s": 0.0
      }
    ],
    "pole_time_s": 81.234,
    "drivers_analysed": 20
  },
  "meta": {
    "source": "openf1",
    "estimated": true,
    "is_stale": false,
    ...
  }
}
```

## Notes

- Routes through `f1_laps_chain` (OpenF1 → fastf1 fallback) and `f1_drivers_chain` for name enrichment.
- Model: [[quali-analysis]] pure functions (`best_lap_per_driver`, `gap_to_pole`, `grid_projection`).
- `meta.estimated: true` — lap data is real telemetry but driver enrichment may be incomplete for partial sessions.
