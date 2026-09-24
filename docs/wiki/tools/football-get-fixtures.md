---
title: football_get_fixtures
type: tool
tags: [football, fixtures]
sources: []
last_updated: 2026-09-25
related: [[football-fixtures-chain]], [[api-football]], [[football-data-org]]
---

# football_get_fixtures

Returns World Cup 2026 fixtures from live providers, else the synthesised group schedule.

## Signature
```python
async def football_get_fixtures(limit: int = 50, offset: int = 0) -> Envelope
```

## Args
`limit` and `offset` paginate the fixtures.

## Returns
`data.fixtures`: list of {home, away, date/group, status, home_goals, away_goals}. via [[football-fixtures-chain]].
