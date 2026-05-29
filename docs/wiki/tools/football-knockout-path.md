---
title: football_knockout_path
type: tool
tags: [football, monte-carlo, intel]
sources: []
last_updated: 2026-05-29
related: [[bracket-sim]], [[football-simulate-bracket]], [[football-groups-chain]]
---

# football_knockout_path

Round-by-round survival probabilities for one team across the full tournament sim.

## Signature
```python
async def football_knockout_path(team: str, iterations: int = 10000, seed: int | None = None) -> dict
```

## Args
- `team` — Team code (e.g. "FRA").
- `iterations` — Simulations (clamped 100..50000).
- `seed` — Optional RNG seed.

## Returns
`data`: {team, reach_r32, reach_r16, reach_qf, reach_sf, reach_final, win}. `meta.estimated: true`.
