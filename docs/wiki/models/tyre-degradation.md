---
title: Tyre Degradation Model
type: model
tags: [f1, tyre, degradation]
sources: []
last_updated: 2026-05-28
related: [[f1-tyre-degradation]], [[f1-predict-pit-strategy]]
---

# Tyre Degradation Model

Fits a linear model (lap_time = intercept + slope × tyre_age) to per-compound lap data.

## Function

`fit_degradation(laps: list[dict], compound: str) -> dict`

## Returns
- `intercept` — baseline lap time in seconds
- `slope` — degradation rate in seconds per lap (positive = slower over time)
- `residual_std` — model fit quality
- `sample_count` — number of valid laps used

## Outlier filtering
Laps with duration > mean + 2σ are treated as SC/in/out laps and excluded.

## Source
`src/sportiq/f1/models/tyre_deg.py`
