---
title: Pit Strategy Predictor
type: model
tags: [f1, pit-stop, strategy]
sources: []
last_updated: 2026-05-28
related: [[f1-predict-pit-strategy]], [[tyre-degradation-model]], [[undercut-model]]
---

# Pit Strategy Predictor

Predicts optimal pit-stop timing and tyre compound sequence for the remainder of a race.

## Function

`predict(laps, stints, weather, current_lap, total_laps, pit_loss_s=22.0) -> dict`

## Algorithm
1. Determine current compound from most recent stint.
2. Fit tyre degradation per compound using available laps.
3. If rainfall detected → immediate stop for INTER.
4. If projected lap-time loss > pit_loss_s OR remaining > safe_window_laps → 1 stop.
5. If remaining > 35 laps and slope > 0.07 → consider 2 stops.

## Returns
- `stop_laps` — recommended pit lap numbers
- `compound_sequence` — compound for each stint
- `expected_finish_position` — None (Phase 3; modelled in Phase 4)
- `confidence` — 0.0–1.0 based on sample quality

## Source
`src/sportiq/f1/models/pit_strategy.py`
