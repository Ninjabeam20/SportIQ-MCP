---
title: cricket_find_value_bets
type: tool
tags: [cricket, odds, value-betting, ipl]
sources: [theodds-cricket-adapter]
last_updated: 2026-09-02
related: [[cricket-win-probability-model]], [[football-find-value-bets]], [[cricket-get-live-odds]]
---

# cricket_find_value_bets

IPL-only odds scan. **`data.value_bets` is always `[]` today.** A cricket
team-strength model is not wired into this tool (unlike football Elo/Poisson).
Scoring edges against a neutral 50/50 prior would flag every market underdog,
which would be misleading. The tool still reports `events_analysed` so callers
know whether odds were available. For raw de-vigged prices use
[[cricket-get-live-odds]]. Real edge detection lands when a cricket win model
is wired (see [[cricket-head-to-head]] / [[cricket-win-probability-model]]).

## Parameters

| Name | Type | Default | Notes |
| :--- | :--- | :--- | :--- |
| `team` | `str \| None` | `None` | Optional team filter (case-insensitive substring). |
| `min_edge` | `float` | `0.05` | Informational only until bets are emitted. |

## Response shape

```json
{
  "data": {
    "value_bets": [],
    "events_analysed": 8,
    "min_edge": 0.05,
    "model": "neutral_baseline",
    "note": "no bets emitted until a cricket win model is wired"
  },
  "meta": {
    "source": "theodds",
    "estimated": true
  }
}
```

`events_analysed` is 0 outside the IPL season (~March–May) when The Odds API
lists no IPL events. That is an empty market, not an outage.

## Error codes

| Code | Condition |
| :--- | :--- |
| `INVALID_INPUT` | `min_edge` outside `[0, 1]`. |
| `ALL_SOURCES_FAILED` | `THEODDS_KEY` unset or TheOdds API unreachable and no stale cache. |

## Chain

Reuses the existing `cricket:odds` `FallbackChain` (single adapter: `TheOddsCricketAdapter`; 5min fresh / 24h stale TTL). No new chain required.
