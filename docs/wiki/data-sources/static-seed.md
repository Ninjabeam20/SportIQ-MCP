---
title: Static Seed
type: data-source
tags: [cricket, squad, static]
sources: []
last_updated: 2026-05-27
related: [[cricket-squad-chain]]
---

# Static Seed

Local JSON reader bundled with the package. Always enabled, no credentials, no network — it is the always-on terminator for the squad chain so `cricket_get_squad` is guaranteed to return a response even when every upstream is down.

## Where the data lives

`src/sportiq/cricket/data/squads.json` — ships with the package. Phase 1 includes the 10 IPL 2026 franchises:

- CSK, MI, RCB, KKR, RR, DC, PBKS, SRH, LSG, GT

Each team maps to a list of `{name, role, credits}` objects. Roles are Dream11-flavored: `BAT`, `BOWL`, `ALL`, `WK-BAT`.

## When it serves

`StaticSeedSquadAdapter` is the final adapter in [[cricket-squad-chain]]. It serves whenever upstream adapters (cricapi) fail or return nothing. Because the JSON ships with the package, it cannot fail at runtime — the chain always terminates.

## Adapter behavior

- Constructor never raises.
- `healthcheck()` returns `True` iff `squads.json` is present on disk.
- `fetch(team=...)` returns `{"players": [...], "team": ..., "source": "static_seed"}`. Lookup is case-insensitive on the team code.
- `fetch()` with no `team` returns `{"squads": {...}, "source": "static_seed"}` — all teams.

## Phase 2 outlook

`venues.json` joins this directory in Phase 2 to seed F1/cricket venue lookups. The adapter pattern stays the same; one class per data file.
