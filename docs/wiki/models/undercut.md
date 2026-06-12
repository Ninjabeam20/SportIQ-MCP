---
title: Undercut Window Model
type: model
tags: [f1, undercut, strategy]
sources: [f1db]
last_updated: 2026-06-12
related: [[f1-undercut-window]], [[f1-predict-pit-strategy]], [[f1db]]
---

# Undercut Window Model

Pure-arithmetic calculator: determines if a pit stop now will let the attacker overtake the target car after exiting the pits.

## Function

`undercut_window(driver_pace_s, target_pace_s, pit_loss_s, fresh_tyre_delta_s, gap_to_target_s) -> dict`

## Logic
`net_gain_per_lap = fresh_tyre_delta_s − (driver_pace − target_pace)`
`laps_to_clear = ceil((gap + pit_loss) / net_gain_per_lap)`

Viable if `laps_to_clear ≤ 10`. Marginal if `5 < laps_to_clear ≤ 10`.

## Pit loss is per-circuit (not flat)

`pit_loss_s` is no longer a flat `22.0s`. [[f1-undercut-window]] resolves the
session's circuit and passes the **measured** per-circuit pit loss from
`circuits.json` (~20.5s Monte Carlo → ~31.9s Silverstone), measured from OpenF1
laps as `in_lap + out_lap − 2 × clean-lap baseline` (true time LOST by pitting —
see [[f1db]] for why F1DB transit times are not used). Unknown circuit → `22.0s`
default, `meta.circuit_profile: false`. The model itself stays pure — it just
receives whatever `pit_loss_s` the tool resolved.

## Source
`src/sportiq/f1/models/undercut.py`
