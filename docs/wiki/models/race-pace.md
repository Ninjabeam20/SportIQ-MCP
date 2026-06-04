---
title: Race Pace Comparison Model
type: model
tags: [f1, degradation, race-pace]
sources: []
last_updated: 2026-06-04
related: [[f1-race-pace-compare]], [[f1-tyre-degradation]]
---

# Race Pace Comparison Model

Compares two F1 drivers' race pace by fitting a linear tyre-degradation model per shared compound and computing the fresh-tyre intercept delta.

## Function signature

```python
compare_race_pace(
    laps_a, stints_a,
    laps_b, stints_b,
    driver_a, driver_b,
) -> dict
```

Pure function in `src/sportiq/f1/models/race_pace.py`. No I/O.

## Algorithm

1. Annotate each driver's laps with compound and tyre_life via `annotate_laps_with_stints()` (see [[tyre-degradation-model]]).
2. Collect distinct compounds for each driver from laps with valid `lap_duration`.
3. For each compound in the intersection: call `fit_degradation()` for each driver.
4. Skip compounds where either driver has `sample_count == 0`.
5. `pace_delta_s = intercept_a − intercept_b` — negative means driver_a is faster on fresh tyres.
6. `overall_faster`: driver with more compound-wins; `None` if tied.

## Output fields

| Field | Type | Description |
| :--- | :--- | :--- |
| `driver_a` | int | Race number |
| `driver_b` | int | Race number |
| `by_compound` | list | Per-compound comparison entries |
| `overall_faster` | int\|None | Driver with majority compound wins, or None if tied |
| `compounds_compared` | int | Count of shared compounds with sufficient data |

Each `by_compound` entry: `compound`, `intercept_a/b`, `slope_a/b`, `pace_delta_s`, `faster_driver`, `sample_count_a/b`.

## Edge cases

- No shared compounds → `compounds_compared == 0`, empty `by_compound`, no error.
- Empty lap lists → same as above.
- Exact intercept tie on a compound → neither driver gets a win (neither counted for `overall_faster`).
