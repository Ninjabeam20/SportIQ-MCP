---
title: Pit Strategy Predictor
type: model
tags: [f1, pit-stop, strategy]
sources: [f1db, src/sportiq/f1/models/pit_strategy.py, docs/audits/2026-10-10-sports-model-audit.md]
last_updated: 2026-10-22
related: [[f1-predict-pit-strategy]], [[tyre-degradation]], [[undercut]], [[f1db]], [[f1-session-meta-chain]]
---

# Pit Strategy Predictor

Predicts optimal pit-stop timing and tyre compound sequence for the remainder of a race.

## Function

`predict(laps, stints, weather, current_lap, total_laps, pit_loss_s=22.0) -> dict`

`pit_loss_s` defaults to `22.0` but [[f1-predict-pit-strategy]] passes the
**measured** per-circuit value from [[f1db]] (`circuits.json`) when the session's
circuit resolves (via [[f1-session-meta-chain]]); unknown circuit → `22.0` default with
`meta.circuit_profile: false`. `total_laps` comes from the caller: [[f1-predict-pit-strategy]] uses the
explicit argument, else the regulation distance (305 km, Monaco 260 km) divided by the circuit's lap
length — never the highest lap observed so far (`meta.total_laps_source`).

## Algorithm (since 2026-10-22)
1. **Current tyre:** the compound and age of the stint running at `current_lap` (a stint that starts
   later never sets the age).
2. **Fits:** a tyre-degradation fit per compound ([[tyre-degradation]]). An unfitted compound uses the
   `TYRE_SPECS` delta and rate, anchored on a fitted compound.
3. **Rain:** wet only when at least half of the last 10 weather samples have rainfall
   (`_RAIN_WINDOW = 10`, `_RAIN_SHARE = 0.5`). Then the recommendation is INTER. One wet sample no
   longer flips the strategy.
4. **Stay out vs stop:** with `R` laps remaining, staying out costs `Σ (base_c + slope_c × (age_now + k))`
   for k = 1..R. Stopping costs `pit_loss + old-tyre laps + Σ (base_n + slope_n × (k − 1))` on each legal
   next compound, evaluated at every possible stop lap. The cheapest total wins, and
   `net_saving_s = stay-out total − best one-stop total`.
5. **Legality:** a dry race must use two dry compounds, so when only the current dry compound has been
   used, it is excluded from the next-compound candidates. That stop can be taken at a net loss
   (negative `net_saving_s`). A wet current tyre on a dry track is not forced to stop by this rule.

The audit counterexample (20 laps left, a fresh tyre saving 60 s for a 22 s stop) now recommends the
stop; before, the comparison ignored tyre age and the cumulative saving and said "no stop".

Dirty telemetry is coerced defensively: `None`/blank stint compound or unknown enum
strings fall back to `MEDIUM`; `None` rainfall is treated as `0` (dry).

## Returns
- `stop_laps` — recommended pit lap numbers
- `compound_sequence` — compound for each stint
- `expected_finish_position` — None (Phase 3; modelled in Phase 4)
- `confidence` — 0.0–1.0 based on sample quality
- `net_saving_s` — seconds saved by the best stop versus staying out (negative when the stop is only
  taken to satisfy the two-dry-compound rule)
- `current_tyre_age` — laps on the current set at `current_lap`

## Source
`src/sportiq/f1/models/pit_strategy.py`
