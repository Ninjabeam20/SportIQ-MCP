---
title: Football Form Trends Model
type: model
tags: [football, form, trends]
sources: []
last_updated: 2026-09-11
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
| `xg_for`, `xg_against` | Sum of fixture-level `xg_home`/`xg_away` where available (`None` when no xG data). |
| `recent_trend` | `"improving"`, `"declining"`, or `"stable"` — last-3 vs prior-3 goals comparison. |
| `matches_analysed` | Count of finished fixtures found for this team. |

## Notes

- Looks up fixtures by case-insensitive substring match on `home`/`away` fields.
- Only fixtures with a **finished** `status` (same set as [[results-state]]) count when
  `status` is present; legacy payloads without `status` still use the score-present gate.
- Non-integer goal values are skipped (no crash).
- `recent_trend` requires ≥ 4 completed matches; falls back to `"stable"` otherwise.
- Off-season or unknown teams return `matches_analysed: 0` with all zeros (no error).
