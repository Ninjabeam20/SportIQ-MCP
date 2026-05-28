---
title: cricket_captain_recommendation
type: tool
tags: [cricket, dream11, captain]
sources: []
last_updated: 2026-05-28
related: [[captain-score]], [[cricket-squad-chain]], [[cricket-pitch-data-chain]]
---

# cricket_captain_recommendation

Returns the top-3 captain candidates for a fixture by projected fantasy points. Designed for "who should I C?" queries that don't need a full XI.

## Signature

```python
async def cricket_captain_recommendation(team_a: str, team_b: str, venue: str) -> dict
```

## How it ranks

For every player in both squads, [[captain-score]]'s `expected_points` is computed against the venue's pitch profile, default opposition strength (0.5), and neutral form (55). The three highest scores win.

## Returns

```json
{
  "data": {
    "candidates": [
      {"name": "...", "role": "BAT", "team": "...", "credits": 11.0, "projected_points": 78.4},
      ...
    ]
  },
  "meta": {"source": "model:captain_score", "estimated": true}
}
```

Projections are model output, not Dream11 oracle — `meta.estimated: true` always.
