---
title: football_simulate_bracket
type: tool
tags: [football, monte-carlo, flagship, 2026-format]
sources: [src/sportiq/football/intel_tools.py]
last_updated: 2026-10-22
related: [[bracket-sim]], [[group-sim]], [[poisson-xg]], [[live-conditioning]], [[football-groups-chain]], [[football-what-if]], [[0008-football-fallback-strategy]]
---

# football_simulate_bracket

**Phase 4 flagship**: Monte Carlo the full 48-team World Cup into per-team round + title probabilities.

## Signature
```python
async def football_simulate_bracket(iterations: int = 10000, seed: int | None = None) -> Envelope
```

## Args
- `iterations` — Tournament simulations (clamped 100..20000; ~10k gives ±2%).
- `seed` — Optional RNG seed for reproducibility.

## Returns
`data.teams`: `{code: {reach_r32, reach_r16, reach_qf, reach_sf, reach_final, win}}`
sorted by win probability; `data.champion`; `data.iterations`; `data.tiebreak_fallbacks`.
`meta.estimated: true`, `meta.mode` (`completed` / `in_progress` / `pre_tournament_prior`, see
[[live-conditioning]]), `meta.champion` in completed mode, `meta.iterations`, `meta.conditioned_matches`,
the tiebreak policy, and `meta.default_rating_teams` when any entrant lacks a seed rating.

## Runtime behaviour
- **Completed tournament:** every result is locked, so the tool returns the exact rounds without running
  the Monte Carlo (`meta.iterations == 0`). This is the WC 2026 state since the 2026-07-19 final.
- **Seeded memo:** with `seed` set, the sim output is cached for 6 h under
  `sportiq:football:simmemo:{blake2s(groups, results, ratings, n_iter, seed, version)}`; unseeded calls
  always sample fresh. Cache errors fail open.
- **Off the event loop:** the sim runs in `asyncio.to_thread`. It is an expensive tool, so it shares the
  expensive-tool semaphore and the 30 s per-tool deadline (`UPSTREAM_TIMEOUT` on expiry).

## 2026 format
48 teams, 12 groups, top 2 + 8 best thirds → 32-team knockout (R32 → R16 → QF →
SF → Final). The R32 template and all 495 best-third group combinations use the official encoded
allocation; see [[bracket-sim]].
