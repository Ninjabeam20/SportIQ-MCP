---
title: Value-Bet Detector
type: model
tags: [football, odds, betting, value, devig]
sources: [the-odds-api, poisson-xg-model]
last_updated: 2026-09-11
related: [[football-find-value-bets]], [[football-match-predictor]], [[the-odds-api]], [[poisson-xg-model]]
---

# Value-Bet Detector

Pure-function probability math (`src/sportiq/core/value_bet.py`; re-exported from
`football/models/value_bet.py`) that flags +EV
("value") bets by comparing **de-vigged** bookmaker odds to a model's probabilities.

## The idea

A bookmaker's decimal prices imply probabilities that sum to **more than 1** — the
excess is the bookmaker's margin (the *vig* / *overround*). For a 1X2 market priced
`{home, draw, away}`, the implied probability of each is `1 / decimal_odds`.

**De-vigging** normalises those implied probabilities back to sum 1, giving the
market's view of each outcome's true probability. Where the model's probability
exceeds the de-vigged market probability by a threshold, the bet is +EV.

## Functions

- `implied_prob(decimal_odds) -> 1 / odds`.
- `devig(probs) -> dict` — **multiplicative** (proportional) method: divide each
  implied probability by their sum. Simplest de-vig; assumes the margin is applied
  proportionally across outcomes. Adequate for a comparison baseline (we need a
  yardstick, not a calibrated fair price). Empty / all-zero input returns `{}`.
- `find_value(model_probs, bookmaker, min_edge) -> list[dict]` — for each outcome
  that carries a valid price: `edge = model_prob - devigged_market_prob`; emit
  `{outcome, model_prob, fair_odds (1/model_prob), market_odds, edge, bookmaker}`
  where `edge >= min_edge`. Outcomes with a missing (`None`), non-positive, or
  non-numeric price are skipped. Direct calls to `implied_prob` still raise on
  `<= 0` by design.

## Why multiplicative de-vig

Alternatives (additive, Shin, logarithmic) better recover the *true* price when the
favourite–longshot bias matters. We deliberately keep the simplest method: the tool
surfaces a ranked list of candidate edges for a human/model to judge, not a settled
fair price. Documented here so the choice is explicit and swappable.

## Reuse contract

The model probabilities are **not** computed here — the tool feeds in the output of
the same Elo→Poisson path [[football-match-predictor]] uses
(`poisson_xg.lambdas_from_elo` → `poisson_xg.outcome_probabilities`). One source of
truth for ratings/xG; this module only does the odds arithmetic.
