---
name: f1-tyre-model
description: F1 tyre compound constants, degradation model formulation, undercut logic, and pit-lane loss per circuit. Load when working on pit strategy, tyre deg, or undercut models.
when_to_use: When building or modifying f1_predict_pit_strategy, tyre degradation fits, or undercut calculations.
---

# F1 Tyre Model Skill

## Tyre compounds and static constants

| Compound | base_lap_delta_s | degradation_rate | safe_window_laps | crossover_lap |
| :--- | ---: | ---: | ---: | ---: |
| SOFT | -0.8 | 0.08 | 15 | 12 |
| MEDIUM | 0.0 | 0.05 | 25 | 20 |
| HARD | +0.6 | 0.03 | 40 | 35 |
| INTER | +3.0 | 0.10 | 20 | 15 |
| WET | +6.0 | 0.12 | 15 | 10 |

`base_lap_delta_s`: seconds vs MEDIUM reference. Negative = faster.

## Pit lane loss (static seeds, Phase 3)
Default: 22s. Circuit-specific tuning is a Phase 3.1 follow-up.

## Degradation model
Linear polyfit: `lap_time = intercept + slope × tyre_age`
Outlier filter: drop laps > mean + 2σ (SC laps, in/out laps).
Min 2 valid samples required; returns slope=0 if insufficient data.

## Undercut formula
`net_gain_per_lap = fresh_tyre_delta_s − (attacker_pace − target_pace)`
`laps_to_clear = ceil((gap_to_target + pit_loss) / net_gain_per_lap)`
Viable if `laps_to_clear ≤ 10`. Marginal if `5 < laps_to_clear ≤ 10`.
