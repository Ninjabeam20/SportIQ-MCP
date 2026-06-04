---
title: Football Form Trends Model
type: model
tags: [football, form, trends]
sources: []
last_updated: 2026-06-04
related: [[football-form-trends]], [[poisson-xg]]
---

# Football Form Trends Model

Pure function `compute_form_trends(fixtures, team)` that computes rolling form, goal record, and xG trajectory for a national football team from completed fixture history.

## Output fields

| Field | Description |
|-------|-------------|
| `form_string` | Last-5 results as W/D/L characters, most recent last (e.g. `"WWDLW"`). |
| `wins`, `draws`, `losses` | Counts over all analysed completed matches. |
| `goals_scored`, `goals_conceded` | Cumulative totals. |
| `xg_for`, `xg_against` | Sum of fixture-level `xg_home`/`xg_away` where available (0.0 if no xG data). |
| `recent_trend` | `"improving"`, `"declining"`, or `"stable"` — last-3 vs prior-3 points comparison. |
| `matches_analysed` | Count of completed fixtures found for this team. |

## Notes

- Looks up fixtures by case-insensitive substring match on `home`/`away` fields.
- `recent_trend` requires ≥ 6 completed matches; falls back to `"stable"` otherwise.
- Off-season or unknown teams return `matches_analysed: 0` with all zeros (no error).
