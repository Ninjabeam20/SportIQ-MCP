---
title: football_get_top_scorers
type: tool
tags: [football, scorers]
sources: []
last_updated: 2026-05-29
related: [[football-scorers-chain]], [[api-football]], [[football-data-org]]
---

# football_get_top_scorers

Returns the World Cup 2026 top scorers.

## Signature
```python
async def football_get_top_scorers() -> dict
```

## Args
_(none)_

## Returns
`data.scorers`: list of {name, team, goals, assists}. via [[football-scorers-chain]].
