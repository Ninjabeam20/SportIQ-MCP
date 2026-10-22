---
title: openfootball
type: data-source
tags: [football, fixtures, keyless]
sources: [src/sportiq/football/adapters/openfootball.py]
last_updated: 2026-10-22
related: [[football-fixtures-chain]], [[football-data-org]], [[static-seed]], [[results-state]], [[live-conditioning]]
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
edited ~once/day). During the tournament finished-match scores could **lag several hours** behind
kickoff; wherever `FOOTBALLDATA_KEY` is set, [[football-data-org]] runs first and serves fresher scores.
Since the 2026-07-19 final the file is complete: all 104 matches scored, including 4 shootouts and the
extra-time final (ESP 1–0 ARG). A copy taken 2026-10-22 is the replay test fixture
`tests/fixtures/openfootball/worldcup-2026-complete.json`.

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
| `home_goals` / `away_goals` | goals after extra time (`score.et`) when present, else `score.ft`; `None` if unplayed |
| `regulation_home_goals` / `regulation_away_goals` | `score.ft` (90 minutes) |
| `penalties_home` / `penalties_away` | `score.p` when a shootout was played, else `None` |
| `winner` | winning team **name**: decided by penalties, then the final score; `None` only when level (a group draw) |

The winner uses the same name convention as [[football-data-org]], so [[results-state]] resolves it to a
code and locks the tie. Before 2026-10-22 the adapter read only `score.ft` and hard-coded `winner: None`,
which left the 0–0 final and every shootout undecidable.

Output is normalised to `{"fixtures": [...]}` to match [[api-football]] / [[football-data-org]], so it
is a drop-in chain fallback. Returns the full fixture list (including future, unplayed matches), so it
strictly supersedes [[static-seed]] whenever GitHub is reachable.
