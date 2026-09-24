---
title: Cricket Win Probability Model
type: model
tags: [cricket, model, win-probability, t20]
sources: []
last_updated: 2026-09-25
related: [[cricket-find-value-bets]], [[cricket-player-form-index]]
---

# Cricket Win Probability Model

Heuristic pre-match T20 win probability using three signals:

| Signal | Weight | Source |
| :--- | :--- | :--- |
| Form score (0-100) | 50% | [[form-index]] aggregated |
| H2H win rate (0-1) | 30% | `cricket_head_to_head` supplies an estimated player-edge ratio |
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

Weights (`form=50%, h2h=30%, venue=20%`) are heuristic, not empirically calibrated. The H2H tool passes its estimated player-edge ratio; form and venue remain neutral in that call. The model is not wired into `cricket_find_value_bets`, and it has no Elo or Poisson component.
