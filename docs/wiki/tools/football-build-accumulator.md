---
title: Football Build Accumulator
type: tool
tags: [football, accumulator, value-bets]
sources: [football-find-value-bets, parlay-builder]
last_updated: 2026-06-03
related: [[football-find-value-bets]], [[parlay-builder]], [[football-get-odds]], [[value-bet]]
---

# Football Build Accumulator

Builds a football accumulator (parlay) from the top value bets across live markets, composing the best legs into a combined-odds bet with edge and risk metadata.

## Tool signature

```
football_build_accumulator(legs: int = 3, min_edge: float = 0.05) -> {data, meta}
```

**Args:**
- `legs` — Number of legs to include in the accumulator (2-8). Default 3.
- `min_edge` — Minimum edge threshold per leg (exclusive bounds 0..1). Default 0.05 (5 percentage points).

## Response shape

```json
{
  "data": {
    "legs": [
      {
        "event_id": "abc123",
        "home": "Brazil",
        "away": "Argentina",
        "outcome": "home",
        "model_prob": 0.6100,
        "fair_odds": 1.639,
        "market_odds": 1.85,
        "edge": 0.1200,
        "bookmaker": "betfair"
      }
    ],
    "legs_used": 3,
    "combined_odds": 6.8450,
    "combined_model_prob": 0.2134,
    "combined_edge": 0.0674,
    "risk_flag": false,
    "independence_warning": "Probabilities multiplied under independence assumption. Legs are from different matches."
  },
  "meta": {
    "source": "derived",
    "estimated": true,
    "is_stale": false,
    "data_age_seconds": 0,
    "fallback_used": false,
    "duration_ms": 0
  }
}
```

## Empty / no value bets

When no picks meet the `min_edge` threshold, the tool returns a valid envelope (no error):
- `data.legs_used == 0`, `data.legs == []`
- `combined_odds == 1.0`, `combined_model_prob == 1.0`, `combined_edge == 0.0`
- `risk_flag == false`

## Risk flag

`risk_flag` is `true` when either:
- `combined_odds > 10` (long-odds accumulators have high variance), or
- `legs_used >= 4` (independence assumption degrades with more legs).

## Error codes

| Code | Condition |
|:-----|:----------|
| `INVALID_INPUT` | `legs` not in [2, 8], or `min_edge` not in (0, 1) exclusive. |
| `ALL_SOURCES_FAILED` | The underlying `football_find_value_bets` call failed (no odds source available). |

## Implementation

The tool calls `football_find_value_bets(min_edge=min_edge)` directly (same module) and passes the `value_bets` list to `build_accumulator()` from `sportiq.core.parlay`. It does not route through an additional chain — odds freshness is inherited from the odds chain and reflected in `football_find_value_bets`'s response.

The `meta.source` is `"derived"` to signal that this is a computed result, not a raw upstream response.

## Model

See [[parlay-builder]] for the full deduplication, edge-filter, and combined-odds logic.
