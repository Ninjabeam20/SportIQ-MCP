---
title: The Odds API
type: data-source
tags: [cricket, football, odds]
sources: []
last_updated: 2026-05-29
related: [[cricket-odds-chain]], [[football-odds-chain]], [[cricket-get-live-odds]], [[football-get-odds]]
---

# The Odds API

Live bookmaker head-to-head odds for IPL cricket and the FIFA World Cup 2026.

## Base URL
`https://api.the-odds-api.com/v4`

## Credentials
`THEODDS_KEY` (query param `apiKey`). Missing key → `MissingCredentialsError`; the chain walks past and (if available) serves stale odds, else returns an `ALL_SOURCES_FAILED` envelope.

## Free-tier limits
500 req/month, shared across cricket + football (one `theodds` source/budget). The `Budget` primitive has no per-month unit, so it is gated at a ~16/day slice; on exhaustion the chain serves stale odds within the 24h ceiling. See `.claude/rules/api-budgets.md`.

## Endpoints used
| Endpoint | Sport key | Tool | Chain |
| :-- | :-- | :-- | :-- |
| `/sports/{key}/odds` | `cricket_ipl` | `cricket_get_live_odds` | [[cricket-odds-chain]] |
| `/sports/{key}/odds` | `soccer_fifa_world_cup` | `football_get_odds` | [[football-odds-chain]] |

Params: `regions=uk,eu`, `markets=h2h`, `oddsFormat=decimal`.

## Shape & normalisation
The API returns a JSON **array** of events, each with an opaque event id, the two team names and per-bookmaker markets. Each adapter flattens this to `{event_id, home, away, commence_time, bookmakers: [{name, home, away}]}`, reducing every bookmaker to its h2h home/away decimal price (a Draw outcome, present for football, is dropped). The normaliser is intentionally duplicated per sport-specific adapter rather than shared cross-package; the shared piece is the HTTP client.

## Known limitations
The Odds API uses its own event ids, with no concept of a CricAPI `match_id`. The whole sport list is fetched and the tool layer applies an optional team-name filter; resolving a `match_id` → event id is a deferred follow-up.
