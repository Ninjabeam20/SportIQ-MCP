---
title: football_simulate_bracket
type: tool
tags: [football, monte-carlo, flagship, 2026-format]
sources: []
last_updated: 2026-05-29
related: [[bracket-sim]], [[group-sim]], [[poisson-xg]], [[football-groups-chain]], [[0008-football-fallback-strategy]]
---

# football_simulate_bracket

**Phase 4 flagship**: Monte Carlo the full 48-team World Cup into per-team round + title probabilities.

## Signature
```python
async def football_simulate_bracket(iterations: int = 10000, seed: int | None = None) -> dict
```

## Args
- `iterations` — Tournament simulations (clamped 100..50000; ~10k gives ±2%).
- `seed` — Optional RNG seed for reproducibility.

## Returns
`data.teams`: {code: {reach_r32, reach_r16, reach_qf, reach_sf, reach_final, win}} sorted by win prob; `data.champion`; `data.iterations`. `meta.estimated: true`.

## 2026 format
48 teams, 12 groups, top 2 + 8 best thirds -> 32-team knockout (R32 -> R16 -> QF -> SF -> Final). See [[bracket-sim]] for the seeding caveat.
