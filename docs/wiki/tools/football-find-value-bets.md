---
title: football_find_value_bets
type: tool
tags: [football, odds, betting, value, intel]
sources: [the-odds-api, value-bet, poisson-xg-model]
last_updated: 2026-05-30
related: [[value-bet]], [[football-match-predictor]], [[the-odds-api]], [[football-odds-chain]]
---

# football_find_value_bets

Finds +EV ("value") bets for WC 2026 matches by comparing this server's own
match-outcome probabilities to **de-vigged** live bookmaker odds. Monetises the
odds layer (Phase 4.5) by combining it with the existing match model — pure reuse,
no new data source.

## Signature

```python
async def football_find_value_bets(team: str | None = None, min_edge: float = 0.05) -> dict
```

- `team` — optional case-insensitive substring filter on either side of an event.
- `min_edge` — minimum `model_prob - devigged_market_prob` (0..1); default 0.05.

## How it works

1. Fetch live odds via `football_odds_chain` (reuse) — events of
   `{home, away, bookmakers: [{name, home, draw, away}]}` decimal 1X2 prices.
2. Fetch the draw + Elo ratings via `football_groups_chain` (reuse) — the **same**
   path [[football-match-predictor]] uses.
3. Map each event's full team names → rating codes from the draw payload's `teams`
   block. Events where either side isn't rated are skipped (counted out of
   `events_analysed`).
4. For each rated event: compute `{home_win, draw, away_win}` via
   `poisson_xg.lambdas_from_elo` → `outcome_probabilities` (neutral venue, WC
   default), then run [[value-bet]]'s `find_value` per bookmaker.
5. Aggregate, sort by edge descending.

## Returns

```
data.value_bets:     [{event_id, home, away, outcome, model_prob, fair_odds,
                       market_odds, edge, bookmaker}, ...]  (edge-desc)
data.events_analysed: count of events with both teams rated
data.min_edge:        echoed threshold
meta.estimated:       true
meta.is_stale:        reflects the ODDS freshness (the time-sensitive input)
```

## Scope

**Football only** this round. `football_match_predictor` already yields 1X2
probabilities, a perfect match for 1X2 odds. Cricket has no win-probability model
yet (only Dream11 / form / pitch), so a cricket value-bet tool would require
building a win model first — out of scope (stretch in step10).

## Errors

- `INVALID_INPUT` — `min_edge` outside `[0, 1]`.
- `ALL_SOURCES_FAILED` — no odds source (e.g. `THEODDS_KEY` unset) or no ratings.
