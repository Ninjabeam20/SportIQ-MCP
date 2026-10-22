---
title: football_simulate_group
type: tool
tags: [football, monte-carlo, intel]
sources: [src/sportiq/football/intel_tools.py]
last_updated: 2026-10-22
related: [[group-sim]], [[live-conditioning]], [[football-groups-chain]]
---

# football_simulate_group

Monte Carlo one group inside the full 12-group field, including contextual best-third qualification.

## Signature
```python
async def football_simulate_group(group: str, iterations: int = 5000) -> Envelope
```

## Args
- `group` — Group letter A-L; `"Group A"` and lower case are accepted. An unknown letter returns `NOT_FOUND`.
- `iterations` — Simulations (clamped 100..20000).

## Returns
`data.teams`: `{code: {p_first, p_second, p_third, p_fourth, p_auto_advance,
p_best_third_advance, p_advance, avg_points}}`. `p_advance` is the truthful combined probability,
not just top-two probability: each iteration simulates all 12 groups and selects the eight best
thirds. `meta` exposes `mode` (see [[live-conditioning]]), this group's `conditioned_matches`,
`tiebreak_fallbacks` / `tiebreak_policy`, and `default_rating_teams` when any entrant lacks a seed rating.
The sim runs in `asyncio.to_thread`, under the 30 s per-tool deadline.
