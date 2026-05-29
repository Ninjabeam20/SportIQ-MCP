---
title: football_get_fixtures
type: tool
tags: [football, fixtures]
sources: []
last_updated: 2026-05-29
related: [[football-fixtures-chain]], [[api-football]], [[football-data-org]]
---

# football_get_fixtures

Returns World Cup 2026 fixtures from live providers, else the synthesised group schedule.

## Signature
```python
async def football_get_fixtures() -> dict
```

## Args
_(none)_

## Returns
`data.fixtures`: list of {home, away, date/group, status, home_goals, away_goals}. via [[football-fixtures-chain]].
