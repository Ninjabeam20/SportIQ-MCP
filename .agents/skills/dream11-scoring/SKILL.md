---
name: dream11-scoring
description: Dream11 T20 scoring rules, credit constraints, role constraints, and ILP solver approach for cricket fantasy team building.
when_to_use: When building or modifying Dream11 team selection logic, scoring models, or ILP constraints.
---

# Dream11 Scoring Skill

Mirrors the wiki page at docs/wiki/models/dream11-scoring.md. Load this when working on the Dream11 solver, scoring tables, or captain/VC selection.

## Role constraints (T20)
- WK-BAT: 1–4 players
- BAT: 3–5 players  
- ALL: 1–3 players
- BOWL: 3–5 players
- Total: exactly 11 players
- Max 7 from one team
- Total credits ≤ 100

## Scoring (key events)
- Batting run: +1 pt; Boundary bonus: +1 pt; Six bonus: +2 pts
- 25-run milestone: +4 pts; 50: +8; 75: +12; 100: +16
- Dismissal duck: -2 pts
- Wicket (excl. run-out): +25 pts; 3-wicket haul: +4; 4-wkt: +8; 5-wkt: +16
- Maiden over: +8 pts
- Captain multiplier: 2×; Vice-captain: 1.5×

## ILP approach
PuLP CBC solver. Binary variable per player × role (selected, captain, VC).
Objective: maximize projected_points with C×2 + VC×1.5 boosts.
See models/dream11_solver.py for the full formulation.
