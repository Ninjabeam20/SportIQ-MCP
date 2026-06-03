---
title: cricket_find_value_bets
type: tool
tags: [cricket, odds, value-betting, ipl]
sources: [theodds-cricket-adapter]
last_updated: 2026-06-03
related: [[cricket-win-probability-model]], [[football-find-value-bets]]
---

# cricket_find_value_bets

Returns +EV ("value") bets on upcoming IPL matches by comparing de-vigged
bookmaker head-to-head odds to the server's heuristic win probability model.

## Parameters

| Name | Type | Default | Notes |
| :--- | :--- | :--- | :--- |
| `team` | `str \| None` | `None` | Optional team filter (case-insensitive substring). |
| `min_edge` | `float` | `0.05` | Minimum edge (model_prob − market_prob), 0..1. |

## Response shape

```json
{
  "data": {
    "value_bets": [
      {
        "event_id": "string",
        "home": "Mumbai Indians",
        "away": "Chennai Super Kings",
        "outcome": "home",
        "model_prob": 0.52,
        "fair_odds": 1.923,
        "market_odds": 1.85,
        "edge": 0.07,
        "bookmaker": "bet365"
      }
    ],
    "events_analysed": 8,
    "min_edge": 0.05
  },
  "meta": {
    "source": "theodds",
    "is_stale": false,
    "data_age_seconds": 12,
    "fallback_used": false,
    "duration_ms": 120,
    "estimated": true
  }
}
```

## Model

Win probabilities come from `cricket/models/win_probability.py` — a weighted
combination of form score (50%), H2H win rate (30%), and venue tilt (20%).
When signals are unavailable, the model defaults to 50/50. `meta.estimated: true`
is always set. See [[cricket-win-probability-model]].

De-vig math is the multiplicative method shared with [[football-find-value-bets]]
via `core/value_bet.py`.

## Error codes

| Code | Condition |
| :--- | :--- |
| `INVALID_INPUT` | `min_edge` outside `[0, 1]`. |
| `ALL_SOURCES_FAILED` | `THEODDS_KEY` unset or TheOdds API unreachable and no stale cache. |

## Chain

Reuses the existing `cricket:odds` `FallbackChain` (single adapter: `TheOddsCricketAdapter`; 5min fresh / 24h stale TTL). No new chain required.
