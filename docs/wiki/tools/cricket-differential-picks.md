---
title: cricket_differential_picks
type: tool
tags: [cricket, dream11, differential, low-ownership]
sources: []
last_updated: 2026-05-29
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

Dream11 doesn't expose real ownership over a public API in Phase 2. We proxy from credit cost: `squads.json` credits span 7.0–11.0, mapped **linearly onto a 5%→90% ownership curve** (cheap fringe players are rarely owned; premiums are near-universal), clamped to 1–99. Real ownership lands when the Live Sports Odds RapidAPI server is wired in a later phase.

> Phase 3.1 recalibration (audit finding #4): the old `credits * 7` proxy put even the cheapest 7.0-credit player at 49% — above the default 20% threshold — so the tool **always returned `[]`**. The linear curve maps 7.0 credits to ~5%, restoring function.

`meta.estimated: true` is mandatory until that wiring exists. See plan.md §10 decision #7.

## Returns

```json
{
  "data": {
    "picks": [
      {"name": "...", "role": "BOWL", "team": "...", "credits": 7.5,
       "projected_points": 52.1, "estimated_ownership_pct": 15.6},
      ...
    ],
    "ownership_threshold": 20
  },
  "meta": {"source": "model:captain_score", "estimated": true, "is_stale": false}
}
```
