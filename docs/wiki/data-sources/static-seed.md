---
title: Static Seed
type: data-source
tags: [cricket, squad, pitch, static]
sources: []
last_updated: 2026-05-28
related: [[cricket-squad-chain]], [[cricket-pitch-data-chain]]
---

# Static Seed

Local JSON reader bundled with the package. Always enabled, no credentials, no network — it is the always-on terminator for the squad and pitch-data chains so the depending tools are guaranteed to return a response even when every upstream is down.

## Where the data lives

`src/sportiq/cricket/data/` — ships with the package.

- `squads.json` — Phase 1 seed; expanded in Phase 2 to add 4 internationals.
- `venues.json` — Phase 2 seed (added in commit log on 2026-05-28).

### squads.json coverage

IPL franchises: `CSK, MI, RCB, KKR, RR, DC, PBKS, SRH, LSG, GT` (10 teams, Dream11-flavoured rosters with `name / role / credits`).

Internationals (Phase 2 addition): `IND, AUS, ENG, NZ`.

Roles are `BAT`, `BOWL`, `ALL`, `WK-BAT`.

### venues.json coverage

~14 IPL venues with `{name, city, pitch_type (batting/bowling/balanced), avg_first_innings, avg_chasing, boundary_size_m}`. Used by [[cricket-pitch-data-chain]] and the venue lookup inside [[cricket-build-dream11-team]].

## When it serves

- `StaticSeedSquadAdapter` is the final adapter in [[cricket-squad-chain]]. Whenever upstreams (cricapi) fail, this serves.
- `StaticSeedVenueAdapter` is the *only* adapter in [[cricket-pitch-data-chain]] for Phase 2.

Because the JSON ships with the package, it cannot fail at runtime — the chains always terminate.

## Adapter behaviour

- Constructor never raises.
- `healthcheck()` returns `True` iff the bundled JSON file is present on disk.
- `StaticSeedSquadAdapter.fetch(team=...)` returns the normalised `{"players": [...], "team": ..., "source": "static_seed"}` shape (every player carries its `team`). Lookup is case-insensitive.
- `StaticSeedSquadAdapter.fetch()` with no `team` returns `{"squads": {...}, "source": "static_seed"}` — all teams.
- `StaticSeedVenueAdapter.fetch(venue=...)` returns the venues.json record + `{"key", "source"}`. Lookup is case-insensitive and tolerates the key, full name, or city. Raises `NotFoundError` on miss.
