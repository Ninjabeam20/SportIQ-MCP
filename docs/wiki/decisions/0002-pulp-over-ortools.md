---
title: PuLP over OR-Tools for Dream11 solver
type: decision
tags: [cricket, dream11, solver]
sources: [chat]
last_updated: 2026-05-26
related: [[dream11-scoring]]
---

# ADR 0002 — PuLP over OR-Tools

## Decision

Use `PuLP` (with the bundled CBC solver) for the Dream11 ILP.

## Context

The Dream11 problem is integer linear programming over ~22 candidate players with hard constraints (credits ≤100, ≤7 from one team, role distribution, exactly 11 picks, C ≠ VC).

OR-Tools is the heavyweight option. PuLP is pure Python and CBC ships pre-built. Both can solve this problem in <50ms.

## Consequences

- ~5 MB dependency footprint vs ~50 MB for OR-Tools.
- Familiar Python-natural API. The Dream11 model fits in <50 lines.
- If we ever scale to multi-match GL optimisation (thousands of teams), revisit. That belongs in `BACKLOG.md`, not v1.

## Status

Accepted.
