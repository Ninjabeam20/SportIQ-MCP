---
title: football_match_predictor
type: tool
tags: [football, prediction, intel]
sources: []
last_updated: 2026-05-29
related: [[poisson-xg]], [[football-xg-model]], [[football-groups-chain]]
---

# football_match_predictor

Predicts a single match: most likely scoreline + outcome probabilities.

## Signature
```python
async def football_match_predictor(home_team: str, away_team: str, neutral: bool = True) -> dict
```

## Args
- `home_team` — First team code.
- `away_team` — Second team code.
- `neutral` — True = neutral venue.

## Returns
`data`: {most_likely_score, predicted_winner, home_win, draw, away_win}. `meta.estimated: true`.
