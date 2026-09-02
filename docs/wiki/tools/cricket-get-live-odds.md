---
title: cricket_get_live_odds
type: tool
tags: [cricket, odds]
sources: []
last_updated: 2026-09-02
related: [[cricket-odds-chain]], [[the-odds-api]]
---

# cricket_get_live_odds

Returns live bookmaker head-to-head odds for upcoming/live **IPL** matches (~March–May). An empty `events` list outside that window is a successful empty market, not an outage. Not international/Test cricket. For World Cup 2026 football odds use [[football-get-odds]].

## Signature
```python
async def cricket_get_live_odds(team: str | None = None) -> dict
```

## Args
- `team` — optional team name to filter events (case-insensitive substring, matched against both sides). Omit to return every IPL event.

## Returns
`data.events`: list of `{event_id, home, away, commence_time, bookmakers: [{name, home, away}]}` with decimal h2h prices, via [[cricket-odds-chain]]. Empty when The Odds API lists no IPL events.

## Notes
Requires `THEODDS_KEY`; without it the call returns a clean `ALL_SOURCES_FAILED` envelope. The Odds API uses opaque event ids, so a CricAPI `match_id` cannot yet be resolved — filtering is by team name. See [[the-odds-api]].
