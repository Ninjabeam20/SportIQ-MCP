---
title: football_get_groups
type: tool
tags: [football, groups, wc2026]
sources: []
last_updated: 2026-05-29
related: [[football-groups-chain]], [[static-seed]]
---

# football_get_groups

Returns the World Cup 2026 group draw (12 groups of 4) and the advancement format.

## Signature
```python
async def football_get_groups() -> dict
```

## Args
_(none)_

## Returns
`data.groups` (12 groups), `data.format` (top-2 + 8 best-thirds rule), `data.teams`. via [[football-groups-chain]].
