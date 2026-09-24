---
title: football_get_match_stats
type: tool
tags: [football, team-stats]
sources: []
last_updated: 2026-09-25
related: [[football-team-stats-chain]], [[api-football]], [[football-data-org]]
---

# football_get_match_stats

Returns a team's aggregate World Cup tournament statistics.

## Signature
```python
async def football_get_match_stats(team: int) -> dict
```

## Args
- `team` — API-Football numeric team id.

## Returns
`data.team_stats`: {team, played, wins, goals_for, goals_against}. via [[football-team-stats-chain]].

The football-data.org adapter in that chain cannot currently supply aggregate team stats, so this tool needs API-Football data or a cached result.
