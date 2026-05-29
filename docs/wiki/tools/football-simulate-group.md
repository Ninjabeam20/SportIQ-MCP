---
title: football_simulate_group
type: tool
tags: [football, monte-carlo, intel]
sources: []
last_updated: 2026-05-29
related: [[group-sim]], [[football-groups-chain]]
---

# football_simulate_group

Monte Carlo one group's round-robin into per-team qualification probabilities.

## Signature
```python
async def football_simulate_group(group: str, iterations: int = 5000) -> dict
```

## Args
- `group` — Group letter A-L.
- `iterations` — Simulations (clamped 100..50000).

## Returns
`data.teams`: {code: {p_first, p_second, p_third, p_fourth, p_advance, avg_points}}. `meta.estimated: true`.
