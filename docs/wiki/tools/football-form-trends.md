---
title: Football Form Trends
type: tool
tags: [football, form, xg]
sources: [football_fixtures_chain, form_trends]
last_updated: 2026-06-03
related: [[football-get-fixtures]], [[football-fixtures-chain]], [[football-find-value-bets]], [[football-xg-model]]
---

# Football Form Trends

Returns rolling form, goal record, and xG trajectory for a national football team derived from available fixture data.

## Tool signature

```
football_form_trends(team: str) -> {data, meta}
```

**Args:**
- `team` — Team name (e.g. `"Brazil"`, `"Argentina"`). Case-insensitive. Must be non-empty.

## Response shape

```json
{
  "data": {
    "team": "Brazil",
    "matches_analysed": 5,
    "form_string": "WDLWW",
    "wins": 3,
    "draws": 1,
    "losses": 1,
    "goals_scored": 8,
    "goals_conceded": 3,
    "xg_for": 7.42,
    "xg_against": 2.91,
    "recent_trend": "improving"
  },
  "meta": {
    "source": "api_football",
    "estimated": true,
    "is_stale": false,
    "data_age_seconds": 120,
    "fallback_used": false,
    "duration_ms": 80
  }
}
```

`xg_for` / `xg_against` are `null` if the upstream fixture data carries no `xg_home`/`xg_away` fields.

## Off-season / empty response

When there are no completed fixtures for the requested team, the tool still returns a valid envelope (no error). `data.matches_analysed == 0`, `data.form_string == ""`, and `meta.note` is set to `"No completed fixtures found for this team."`.

## Error codes

| Code | Condition |
|:-----|:----------|
| `INVALID_INPUT` | `team` is blank or empty. |
| `ALL_SOURCES_FAILED` | Every adapter in `football_fixtures_chain` failed and no stale cache is available. |

## Model

Form computation lives in `src/sportiq/football/models/form_trends.py` (`compute_form_trends`). It is a pure function with no I/O:

1. Filter fixtures to those where the team appears as `home_team` or `away_team` (case-insensitive).
2. Drop fixtures where either score is `None` (future matches).
3. Sort ascending by `date`.
4. Derive W/D/L per match from goals-for vs goals-against.
5. `recent_trend` — compares average goals scored in the last 3 matches vs the 3 before that. Requires ≥ 4 completed matches; otherwise returns `"stable"`.

## Chain

Routes through `football_fixtures_chain` (api_football → football_data_org → static seed; 6h TTL).
