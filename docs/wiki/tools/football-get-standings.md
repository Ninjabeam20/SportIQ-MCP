---
title: football_get_standings
type: tool
tags: [football, standings]
sources: []
last_updated: 2026-09-25
related: [[football-standings-chain]], [[api-football]], [[football-data-org]]
---

# football_get_standings

Returns current World Cup 2026 group standings.

## Signature
```python
async def football_get_standings(limit: int = 50, offset: int = 0) -> Envelope
```

## Args
`limit` and `offset` paginate the standings.

## Returns
`data.standings`: list of {rank, team, group, points, played, goals_diff}. via [[football-standings-chain]].
