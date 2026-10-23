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

## Scoring (key events) — profile `dream11-t20-2026-10-10`
Source: official Dream11 T20 table, https://login.dream11.com/games/fantasy-cricket/how-to-play (checked 2026-10-10). Constants live in `src/sportiq/cricket/data/scoring.py`.
- Batting run: +1 pt; Boundary bonus: +4 pts; Six bonus: +6 pts
- Milestones (highest reached only): 25 runs +4; 50 runs +8; 75 runs +12; 100 runs +16
- Dismissal duck: -2 pts (BAT/ALL/WK only, dismissed for 0)
- Dot ball: +1 pt; Wicket (excl. run out): +30 pts; LBW / bowled bonus: +8 pts (each)
- 3-wicket haul: +4 pts; 4-wicket haul: +8 pts; 5-wicket haul: +12 pts
- Maiden over: +12 pts
- Catch: +8 pts; 3-catch bonus: +4 pts
- Stumping: +12 pts
- Run-out (direct): +12 pts; Run-out (indirect): +6 pts
- Captain multiplier: 2×; Vice-captain: 1.5×
- Not modelled: announced lineup +4, playing substitute +4 (per selection, not per innings)

## Strike-rate buckets (≥10 balls faced; never for bowlers)
- >170: +6 pts
- 150.01–170: +4 pts
- 130–150: +2 pts
- 60–70: -2 pts
- 50–59.99: -4 pts
- <50: -6 pts

## Economy buckets (≥2 overs bowled)
- below 5: +6 pts
- 5–5.99: +4 pts
- 6–7: +2 pts
- 10–11: -2 pts
- 11.01–12: -4 pts
- >12: -6 pts

## ILP approach
PuLP CBC solver. Binary variable per player × role (selected, captain, VC).
Objective: maximize projected_points with C×2 + VC×1.5 boosts.
See models/dream11_solver.py for the full formulation.
