---
title: football_get_squad
type: tool
tags: [football, squad]
sources: []
last_updated: 2026-05-29
related: [[football-squad-chain]], [[api-football]], [[static-seed]]
---

# football_get_squad

Returns a national team's World Cup squad.

## Signature
```python
async def football_get_squad(team: str) -> dict
```

## Args
- `team` — Team code or name (e.g. "ARG").

## Returns
`data.squad`: list of {name, number, position, age}. Without an API-Football key the static seed returns an empty-but-valid squad. via [[football-squad-chain]].
