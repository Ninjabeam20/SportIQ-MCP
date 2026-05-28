---
title: Undercut Window Model
type: model
tags: [f1, undercut, strategy]
sources: []
last_updated: 2026-05-28
related: [[f1-undercut-window]], [[f1-predict-pit-strategy]]
---

# Undercut Window Model

Pure-arithmetic calculator: determines if a pit stop now will let the attacker overtake the target car after exiting the pits.

## Function

`undercut_window(driver_pace_s, target_pace_s, pit_loss_s, fresh_tyre_delta_s, gap_to_target_s) -> dict`

## Logic
`net_gain_per_lap = fresh_tyre_delta_s − (driver_pace − target_pace)`
`laps_to_clear = ceil((gap + pit_loss) / net_gain_per_lap)`

Viable if `laps_to_clear ≤ 10`. Marginal if `5 < laps_to_clear ≤ 10`.

## Source
`src/sportiq/f1/models/undercut.py`
