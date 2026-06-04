---
title: cricket_player_matchup
type: tool
tags: [cricket, player, matchup]
sources: []
last_updated: 2026-06-04
related: [[player-matchup]], [[cricket-build-dream11-team]]
---

# cricket_player_matchup

Analyse the head-to-head matchup between two cricket players by comparing their role and career stats, returning an edge assessment and the raw signals used.

## Args

| Param | Type | Description |
|-------|------|-------------|
| `player_a` | `str` | Player ID or name for the first player. |
| `player_b` | `str` | Player ID or name for the second player. Must differ from `player_a`. |

## Return shape

```json
{
  "data": {
    "player_a": "Rohit Sharma",
    "player_b": "Jasprit Bumrah",
    "role_a": "batter",
    "role_b": "bowler",
    "matchup_type": "batter_vs_bowler",
    "edge_holder": "player_a",
    "edge_reason": "Batter avg 45.0 exceeds bowler avg 22.0 by >15% — batter has the edge.",
    "signals": {
      "batting_avg_a": 45.0,
      "batting_avg_b": null,
      "bowling_avg_a": null,
      "bowling_avg_b": 22.0,
      "strike_rate_a": 135.0,
      "strike_rate_b": null
    }
  },
  "meta": {
    "source": "cricapi",
    "estimated": true,
    "is_stale": false
  }
}
```

## Notes

- `meta.estimated: true` — the edge is a heuristic model, not ball-by-ball H2H data.
- Fetches both players concurrently via `player_stats_chain`.
- Returns `INVALID_INPUT` if either player is blank or both are identical.
- Returns `ALL_SOURCES_FAILED` if either player's stats cannot be fetched.
