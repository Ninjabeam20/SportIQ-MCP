---
title: football_what_if
type: tool
tags: [football, monte-carlo, intel, what-if]
sources: [bracket-sim]
last_updated: 2026-10-22
related: [[bracket-sim]], [[football-simulate-bracket]], [[football-knockout-path]], [[football-groups-chain]]
---

# football_what_if

Replay World Cup 2026 from a chosen stage, keeping every real result before it, optionally flipping one decided knockout tie.

## Signature
```python
async def football_what_if(
    replay_from: Literal["group", "r32", "r16", "qf", "sf", "final"] = "group",
    flip_winner_of: str | None = None,
    iterations: int = 10000,
    seed: int | None = None,
) -> Envelope
```

## Args
- `replay_from` — Stage to re-simulate from. `"group"` keeps no real results (a full pre-tournament replay); `"r32"` keeps the group stage; `"final"` keeps everything before the final and simulates only the final.
- `flip_winner_of` — Optional decided knockout tie to flip, as two codes or names joined by a hyphen in any order (`"ESP-FRA"`). It must be a tie played before `replay_from`, else `INVALID_INPUT`.
- `iterations` — Simulations (clamped 100..20000).
- `seed` — Optional RNG seed. Seeded runs are memoised for 6 h (`sportiq:football:simmemo:*`).

## Returns
`data`: same shape as [[football-simulate-bracket]] (`teams`, `champion`, `iterations`). `meta.mode: "what_if"`, `meta.replay_from`, `meta.flipped` (`{tie, winner}` or null), `meta.estimated: true`, plus the usual freshness fields.

## How it works
`results_state.truncate_results_state` drops real results from `replay_from` on, using each knockout tie's round label (`knockout_rounds`; unlabelled ties and the third-place match are never kept). `flip_knockout_winner` swaps one locked winner; the recorded goals (and so the opt-in live-Elo walk) stay as played. The truncated state then conditions the normal bracket Monte Carlo.

## Example
```python
football_what_if(replay_from="final", flip_winner_of="ESP-FRA", seed=7)
# France replaces Spain in the final against Argentina.
```
