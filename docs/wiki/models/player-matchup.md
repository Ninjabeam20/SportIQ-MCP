---
title: Player Matchup Model
type: model
tags: [cricket, matchup, heuristic]
sources: []
last_updated: 2026-06-04
related: [[cricket-player-matchup]]
---

# Player Matchup Model

A role-aware heuristic that classifies two players' confrontation type and assigns an edge holder based on career averages and strike rate, with no I/O.

## Location

`src/sportiq/cricket/models/player_matchup.py` — pure function `compute_matchup(stats_a, stats_b) -> dict`.

## Matchup type classification

| Role A | Role B | matchup_type |
|--------|--------|--------------|
| batter / wk-batter | batter / wk-batter | `batter_vs_batter` |
| bowler | bowler | `bowler_vs_bowler` |
| batter / wk-batter | bowler (either order) | `batter_vs_bowler` |
| anything else | anything else | `other` |

## Edge logic

### batter_vs_bowler

- Batter edge: `batting_avg > bowling_avg * 1.15`
- Bowler edge: `bowling_avg < batting_avg * 0.85`
- Otherwise: `neutral`
- Any `None` stat → `neutral` (no crash)

### batter_vs_batter

- Higher strike rate wins.
- Neutral if `abs(sr_a - sr_b) / max(sr_a, sr_b) < 0.05` (within 5%).
- Any `None` stat → `neutral`

### bowler_vs_bowler / other

Always `neutral`.

## Signals dict

Always returned, even when `None`:

```python
{
  "batting_avg_a", "batting_avg_b",
  "bowling_avg_a", "bowling_avg_b",
  "strike_rate_a", "strike_rate_b"
}
```
