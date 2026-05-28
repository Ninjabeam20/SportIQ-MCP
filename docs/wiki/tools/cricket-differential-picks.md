---
title: cricket_differential_picks
type: tool
tags: [cricket, dream11, differential, low-ownership]
sources: []
last_updated: 2026-05-28
related: [[captain-score]], [[cricket-build-dream11-team]]
---

# cricket_differential_picks

Surfaces low-ownership players with positive projected upside — the move you make when you're chasing the leaderboard, not playing safe.

## Signature

```python
async def cricket_differential_picks(
    team_a: str,
    team_b: str,
    venue: str,
    ownership_threshold: int = 20,
) -> dict
```

## Ownership is estimated

Dream11 doesn't expose real ownership over a public API in Phase 2. We proxy with `estimated_ownership_pct = credits * 7` (capped at 95) — lower-credit players tend to be picked less. Real ownership lands when the Live Sports Odds RapidAPI server is wired in a later phase.

`meta.estimated: true` is mandatory until that wiring exists. See plan.md §10 decision #7.

## Returns

```json
{
  "data": {
    "picks": [
      {"name": "...", "role": "BOWL", "team": "...", "credits": 7.5,
       "projected_points": 52.1, "estimated_ownership_pct": 52.5},
      ...
    ],
    "ownership_threshold": 20
  },
  "meta": {"source": "model:captain_score", "estimated": true}
}
```
