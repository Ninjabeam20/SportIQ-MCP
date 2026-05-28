---
title: Dream11 Solver (PuLP ILP)
type: model
tags: [cricket, dream11, ilp, pulp, cbc]
sources: []
last_updated: 2026-05-28
related: [[cricket-build-dream11-team]], [[dream11-scoring]], [[captain-score]], [[0002-pulp-over-ortools]]
---

# Dream11 Solver

Binary integer linear program that picks the optimal 11 + captain + vice-captain under T20 fantasy constraints. Lives at `src/sportiq/cricket/models/dream11_solver.py`.

## Decision variables

For `n` candidates:

- `x_i ∈ {0, 1}` — whether candidate `i` is in the XI.
- `c_i ∈ {0, 1}` — whether candidate `i` is captain.
- `v_i ∈ {0, 1}` — whether candidate `i` is vice-captain.

## Constraints

| Constraint | Form |
| :--- | :--- |
| Squad size | `sum(x_i) == 11` |
| Credit cap | `sum(credits_i * x_i) <= 100` |
| Per-team cap | `sum(x_i for i in team_t) <= 7` for each team `t` |
| Keeper count | `1 <= sum(x_i where role in {WK, WK-BAT}) <= 4` |
| Batter count | `3 <= sum(x_i where role == BAT) <= 5` |
| All-rounder count | `1 <= sum(x_i where role == ALL) <= 3` |
| Bowler count | `3 <= sum(x_i where role == BOWL) <= 5` |
| Captain exists | `sum(c_i) == 1` |
| Vice-captain exists | `sum(v_i) == 1` |
| C ≠ VC | `c_i + v_i <= 1` for each `i` |
| C in XI | `c_i <= x_i` for each `i` |
| VC in XI | `v_i <= x_i` for each `i` |

## Objective

```
maximise  sum_i ( pp_i * x_i + pp_i * c_i * (captain_mult - 1)
                              + pp_i * v_i * (vc_mult - 1) )
```

where `pp_i` is `projected_points` (from [[captain-score]]) and the bonus coefficients come from [[dream11-scoring]] — `1.0` for captain (effective x2), `0.5` for vice-captain (effective x1.5).

## Solver

PuLP's `COIN_CMD` backend, which picks up the system `cbc` binary off PATH (on macOS arm64: `brew install cbc`). The bundled `PULP_CBC_CMD` falls over on Apple Silicon — see commit notes.

## Infeasibility raises

If no XI satisfies the constraints (credit cap too tight, all candidates from one team, no keeper in the pool, fewer than 11 candidates) the solver raises `InvalidInputError`. The wrapping tool converts that into the `INVALID_INPUT` error envelope.

## Performance

A 22-candidate pool resolves in well under 500 ms on commodity hardware. The model has ~66 binary variables; CBC's MILP machinery is overkill for this scale, but the formulation stays portable to larger pools (e.g. when [[cricket-build-dream11-team]] eventually accepts >2 teams for stacked tournaments).
