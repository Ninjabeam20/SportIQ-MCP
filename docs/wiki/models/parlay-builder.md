---
title: Parlay Builder
type: model
tags: [parlay, accumulator, core]
sources: [football-build-accumulator]
last_updated: 2026-10-22
related: [[football-build-accumulator]], [[football-find-value-bets]], [[value-bet]]
---

# Parlay Builder

Pure function that selects the best legs from a list of value-bet picks and computes the combined odds, combined model probability, and combined edge for an accumulator bet, under the independence assumption.

## Location

`src/sportiq/core/parlay.py` — `build_accumulator(picks, legs, min_edge)`

## Algorithm

Given a list of picks (each with `edge`, `model_prob`, `market_odds` or `decimal_odds`, and a match identifier):

1. **Edge filter** — drop picks where `edge < min_edge`.
2. **Deduplication** — group by match (using `event_id` or `match_id`); keep one pick per match (highest edge wins).
3. **Selection** — sort descending by edge; take the top `legs` picks. If fewer picks are available than `legs`, use all (no error — `legs_used` reflects actual count).
4. **Combined statistics:**
   - `combined_odds = product(market_odds for each leg)`
   - `combined_model_prob = product(model_prob for each leg)` — independence assumed
   - `combined_edge = combined_model_prob - (1 / combined_odds)`

## Risk flag

`risk_flag = True` when `combined_odds > 10` or `legs_used >= 4`. High combined odds and many legs both increase variance; the flag is a signal to the caller, not a hard veto.

## Independence warning

The output always includes `independence_warning`:

> "Probabilities multiplied under independence assumption. Legs are from different matches."

Match outcomes are not independent in general (shared tournament context, weather, referee effects), but the model treats them as such. The warning is always present to surface this assumption to the consumer.

## Empty picks

When no picks survive the filter (or the input list is empty), returns:
- `legs_used == 0`, `legs == []`
- `combined_odds`, `combined_model_prob`, `combined_edge` all `None`, with
  `note: "No legs met the edge threshold."` — not `1.0`, because an empty product would read as a
  certain even-money accumulator (changed 2026-10-22)
- `risk_flag == False`

## Odds basis

Every result carries `combined_odds_basis: "best price per leg across bookmakers (not a
single-bookmaker acca)"`. Each leg's price can come from a different bookmaker, so no single book
necessarily offers the combined odds.

## Bounds enforcement

The `legs` parameter is bounded (2-8) in the **tool layer** only (`football_build_accumulator`). The pure `build_accumulator` function has no bounds check — it is usable for any sport or test scenario with any number of legs.

## Cross-sport reuse

`build_accumulator` is in `sportiq.core` (not `sportiq.football`) intentionally — it is reusable for cricket or F1 accumulator features without modification.
