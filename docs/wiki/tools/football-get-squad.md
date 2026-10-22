---
title: football_get_squad
type: tool
tags: [football, squad]
sources: [src/sportiq/football/tools.py, src/sportiq/football/adapters/static_seed.py]
last_updated: 2026-10-22
related: [[football-squad-chain]], [[api-football]], [[static-seed]]
---

# football_get_squad

Returns a national team's World Cup squad from API-Football; with no key it returns an empty-but-valid squad and says why.

## Signature
```python
async def football_get_squad(team: str) -> Envelope
```

## Args
- `team` — Team code, name or API-Football numeric team id (non-empty, ≤100 chars). Only a numeric id can
  reach API-Football's `/players/squads`; a code such as `"ARG"` is refused before any request (no quota
  spent) and the chain falls through to the static seed.

## Returns
`data.squad`: list of `{name, number, position, age}` via [[football-squad-chain]]. SportIQ bundles no
football squads (the hand-written seed was removed on 2026-10-22), so without `APIFOOTBALL_KEY` the squad is
empty and `meta.note` is "No bundled squads; set APIFOOTBALL_KEY for live squads."
