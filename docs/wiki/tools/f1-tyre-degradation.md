---
title: f1_tyre_degradation
type: tool
tags: [f1, tyre, degradation, intel]
sources: []
last_updated: 2026-05-29
related: [[f1-laps-chain]], [[f1-stints-chain]], [[tyre-degradation-model]]
---

# f1_tyre_degradation

Fits a linear tyre-degradation model (lap_time = intercept + slope × tyre_age) for a driver and compound in a session.

## Signature

```python
async def f1_tyre_degradation(session_key: int, driver_number: int, compound: str) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`).
- `driver_number` — Driver number (e.g. 1 for Verstappen).
- `compound` — Tyre compound: `SOFT`, `MEDIUM`, `HARD`, `INTER`, or `WET`.

## Success response

```json
{
  "data": {
    "compound": "MEDIUM",
    "intercept": 90.2,
    "slope": 0.048,
    "residual_std": 0.31,
    "sample_count": 18
  },
  "meta": {"source": "openf1", "is_stale": false}
}
```

`slope` is in seconds per lap — positive means the tyre is degrading.

## Telemetry merge (Phase 3.1, audit finding #1)

OpenF1's `/laps` endpoint carries **no `compound` and no `tyre_life`** — those live on `/stints`. The tool fetches both [[f1-laps-chain]] and [[f1-stints-chain]] and merges them (`tyre_life = tyre_age_at_start + (lap_number - lap_start)`) before fitting, so the model runs on real telemetry instead of silently falling back to `TyreSpec` constants.

Stint enrichment is **best-effort**: laps are required, but if the stints source is down the tool fits on whatever the laps already carry rather than failing. `meta.stint_enrichment` reports whether the merge ran.

## Chain

[[f1-laps-chain]] + [[f1-stints-chain]]
