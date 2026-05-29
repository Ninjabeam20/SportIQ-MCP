---
title: football_get_odds
type: tool
tags: [football, odds]
sources: []
last_updated: 2026-05-29
related: [[football-odds-chain]], [[the-odds-api]]
---

# football_get_odds

Returns live bookmaker head-to-head odds for upcoming World Cup 2026 matches.

## Signature
```python
async def football_get_odds(team: str | None = None) -> dict
```

## Args
- `team` — optional team name to filter events (case-insensitive substring, matched against both sides). Omit to return every WC event.

## Returns
`data.events`: list of `{event_id, home, away, commence_time, bookmakers: [{name, home, draw, away}]}` with decimal 1X2 prices, via [[football-odds-chain]].

## Notes
Requires `THEODDS_KEY`; without it the call returns a clean `ALL_SOURCES_FAILED` envelope. WC markets are 1X2 — the Draw price is captured alongside home/away. See [[the-odds-api]].
