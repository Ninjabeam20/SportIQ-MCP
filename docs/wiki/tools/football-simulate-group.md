---
title: football_simulate_group
type: tool
tags: [football, monte-carlo, intel]
sources: []
last_updated: 2026-07-14
related: [[group-sim]], [[football-groups-chain]]
---

# football_simulate_group

Monte Carlo one group inside the full 12-group field, including contextual best-third qualification.

## Signature
```python
async def football_simulate_group(group: str, iterations: int = 5000) -> dict
```

## Args
- `group` — Group letter A-L.
- `iterations` — Simulations (clamped 100..20000).

## Returns
`data.teams`: `{code: {p_first, p_second, p_third, p_fourth, p_auto_advance,
p_best_third_advance, p_advance, avg_points}}`. `p_advance` is the truthful combined probability,
not just top-two probability: each iteration simulates all 12 groups and selects the eight best
thirds. `meta` exposes conditioning counts plus `tiebreak_fallbacks` / `tiebreak_policy`.
