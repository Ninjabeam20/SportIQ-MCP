---
title: cricket_build_dream11_team
type: tool
tags: [cricket, dream11, ilp, flagship]
sources: []
last_updated: 2026-09-25
related: [[dream11-solver]], [[dream11-scoring]], [[captain-score]], [[cricket-squad-chain]], [[cricket-pitch-data-chain]]
---

# cricket_build_dream11_team

Phase 2 flagship #1. Returns an optimal Dream11 XI plus captain and vice-captain for a single fixture, honoring all T20 fantasy constraints.

## Signature

```python
async def cricket_build_dream11_team(
    match_id: str | None = None,
    team_a: str | None = None,
    team_b: str | None = None,
    venue: str | None = None,
    strategy: str = "balanced",
) -> Envelope
```

`team_a` / `team_b` accept any team code or name resolvable by [[cricket-squad-chain]] (`MI`, `CSK`, `IND`, etc.). `venue` accepts a venues.json key, the official venue name, or the city — see [[static-seed]].

Pass `match_id` to resolve teams and venue through the fixtures chain, falling back to the scorecard chain. Alternatively, pass `team_a`, `team_b`, and `venue` directly. A missing or unresolved venue returns a structured error.

## Constraints enforced (per call)

- Exactly 11 players in the XI.
- Total credits ≤ 100.
- ≤ 7 players from any single team.
- 1–4 wicket-keepers (WK or WK-BAT), 3–5 batters, 1–3 all-rounders, 3–5 bowlers.
- Captain and vice-captain distinct, both in the XI.

## Returns

```json
{
  "data": {
    "players": [{"name": "...", "role": "...", "credits": 9.0, "team": "...", "projected_points": 65.3}, ...],
    "captain": "<name>",
    "vice_captain": "<name>",
    "total_credits": 99.5,
    "total_projected_points": 612.3
  },
  "meta": {
    "source": "model:dream11_solver",
    "venue": "Wankhede Stadium",
    "strategy": "balanced",
    "estimated": true
  }
}
```

`total_projected_points` already includes the captain x2 and vice-captain x1.5 fantasy boosts. `meta.estimated: true` because projections come from the in-house [[captain-score]] model, not a live oracle.

## Strategy variants

Phase 2 ships `balanced` only. `aggressive` (top-heavy batting) and `differential` (low-ownership tilt) land in 2.1 as different `(lo, hi)` tuples per role inside the solver.
