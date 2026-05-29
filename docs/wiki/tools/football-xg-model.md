---
title: football_xg_model
type: tool
tags: [football, xg, intel]
sources: []
last_updated: 2026-05-29
related: [[poisson-xg]], [[elo]], [[football-groups-chain]]
---

# football_xg_model

Estimates a match's expected goals and win/draw/loss probabilities from Elo.

## Signature
```python
async def football_xg_model(home_team: str, away_team: str, neutral: bool = True) -> dict
```

## Args
- `home_team` — First team code.
- `away_team` — Second team code.
- `neutral` — True = neutral venue (WC default).

## Returns
`data`: {expected_home_goals, expected_away_goals, home_win, draw, away_win}. `meta.estimated: true`.
