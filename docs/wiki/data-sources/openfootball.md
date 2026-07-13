---
title: openfootball
type: data-source
tags: [football, fixtures, keyless]
sources: []
last_updated: 2026-07-14
related: [[football-fixtures-chain]], [[football-data-org]], [[static-seed]]
---

# openfootball

Keyless, public-domain source for World Cup 2026 fixtures **with real final scores**, filled in as
matches are played. Sits above the static seed in the fixtures chain so the keyless (zero-API-key)
deployment can still surface actual results instead of a scores-less schedule.

## URL
`https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json`

## Credentials
None. No token, no quota (`budget = None`).

## Update cadence / caveat
The upstream is hand-maintained (a wiki-style text source regenerated to JSON via GitHub Action,
edited ~once/day). Finished-match scores are correct but can **lag several hours** behind kickoff.
Wherever `FOOTBALLDATA_KEY` is set, [[football-data-org]] runs first and serves fresher scores.

## Parse mapping
Top-level `matches[]`; each match →

| Output key | Source |
| :-- | :-- |
| `home` / `away` | `team1` / `team2` |
| `date` | `date` (`YYYY-MM-DD`) |
| `group` | `group` |
| `match_id` | native `id` when present, else `None` |
| `stage` | `round` |
| `status` | `FINISHED` if `score.ft` is a 2-list, else `SCHEDULED` |
| `home_goals` / `away_goals` | `score.ft[0]` / `score.ft[1]`, else `None` |
| `winner` | `None` (winner inferred from decisive scores; level knockouts stay undecidable) |

Output is normalised to `{"fixtures": [...]}` to match [[api-football]] / [[football-data-org]], so it
is a drop-in chain fallback. Returns the full fixture list (including future, unplayed matches), so it
strictly supersedes [[static-seed]] whenever GitHub is reachable.
