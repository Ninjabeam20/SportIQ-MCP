---
title: f1_predict_pit_strategy
type: tool
tags: [f1, pit-stop, strategy, intel, flagship]
sources: []
last_updated: 2026-05-28
related: [[f1-laps-chain]], [[f1-stints-chain]], [[f1-weather-chain]], [[pit-strategy-model]]
---

# f1_predict_pit_strategy

**Phase 3 flagship tool.** Predicts optimal pit-stop timing and tyre compound sequence for the remainder of a race, using tyre-degradation fits on live OpenF1 telemetry.

## Signature

```python
async def f1_predict_pit_strategy(
    session_key: int,
    driver_number: int,
    current_lap: int,
    total_laps: int,
) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`). Must point to a Race session.
- `driver_number` — Driver number (e.g. 1 for Verstappen).
- `current_lap` — Current race lap at prediction time.
- `total_laps` — Total race laps (available from session metadata).

## Success response

```json
{
  "data": {
    "stop_laps": [28, 48],
    "compound_sequence": ["SOFT", "MEDIUM", "HARD"],
    "confidence": 0.74,
    "rationale": "2-stop strategy preferred — SOFT degrading at 0.09s/lap, crossover at lap 28."
  },
  "meta": {"source": "openf1", "is_stale": false}
}
```

`stop_laps` is the recommended lap number for each pit stop. `compound_sequence` lists the compound for each stint (length = len(stop_laps) + 1).

## Model

See [[pit-strategy-model]] for algorithm details. Key inputs: per-compound tyre-degradation fits ([[tyre-degradation-model]]), weather rainfall flag ([[f1-weather-chain]]), current stint from stints data ([[f1-stints-chain]]).

## Chains

[[f1-laps-chain]], [[f1-stints-chain]], [[f1-weather-chain]]
