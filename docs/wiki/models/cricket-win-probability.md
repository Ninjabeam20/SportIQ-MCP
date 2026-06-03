---
title: Cricket Win Probability Model
type: model
tags: [cricket, model, win-probability, t20]
sources: []
last_updated: 2026-06-03
related: [[cricket-find-value-bets]], [[cricket-player-form-index]]
---

# Cricket Win Probability Model

Heuristic pre-match T20 win probability using three signals:

| Signal | Weight | Source |
| :--- | :--- | :--- |
| Form score (0-100) | 50% | [[form-index]] aggregated |
| H2H win rate (0-1) | 30% | H2H data (stubbed at 0.5 until Feature 2) |
| Venue tilt (0-1) | 20% | [[pitch-report]] `batting_friendly` |

Output: `{"team_a": float, "team_b": float}` summing to 1. No draw (T20 only).
Always flagged `meta.estimated: true`.

## Implementation

`src/sportiq/cricket/models/win_probability.py` — pure function, no I/O.

```python
win_prob(team_a_signals: dict, team_b_signals: dict) -> {"team_a": float, "team_b": float}
```

Each signals dict accepts optional keys: `form_score` (0–100), `h2h_win_rate` (0–1), `venue_tilt` (0–1). Missing keys default to neutral (0.5).

## Graceful degradation

All inputs optional — the model never errors. Missing form defaults to 50 (neutral). Missing H2H defaults to 0.5 (coin flip). Missing venue_tilt defaults to 0.5 (no home/away tilt). The result with all defaults is exactly 50/50.

## Calibration notes

Weights (`form=50%, h2h=30%, venue=20%`) are calibrated for T20 heuristics. No Elo or Poisson component yet — this is intentionally simple for Phase 1C. Feature 2 (H2H analyzer) will wire real H2H win rates; Feature 4 (form trends) will supply rolling form scores.
