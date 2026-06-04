---
title: Qualifying Analysis Model
type: model
tags: [f1, qualifying, grid]
sources: []
last_updated: 2026-06-04
related: [[f1-qualifying-analysis]], [[tyre-degradation-model]]
---

# Qualifying Analysis Model

Pure functions that derive best-lap ranking, gap-to-pole seconds, and projected grid from raw OpenF1 lap data.

## Functions

### `best_lap_per_driver(laps)`

Scans the laps list from OpenF1 `/laps` and extracts the minimum valid `lap_duration` per `driver_number`. Invalid (None, ≤ 0, non-numeric) laps are skipped.

### `gap_to_pole(best_laps)`

Computes `gap_seconds = driver_best - pole_time` for each driver. Pole driver has gap 0.0. Returns sorted ascending by gap.

### `grid_projection(gaps, driver_info)`

Builds the projected grid by mapping gap-sorted driver numbers to `{position, driver_number, full_name, team_name, best_lap_gap_s}`. Enrichment uses the `/drivers` payload; missing drivers fall back to `"Driver #N"`.

## Notes

- All three functions are pure (no I/O), composable, and used directly by `f1_qualifying_analysis`.
- Does not model grid penalties, parc fermé failures, or fastest Q3 supersessions.
