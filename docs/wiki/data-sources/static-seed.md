---
title: Static Seed
type: data-source
tags: [cricket, squad, pitch, static]
sources: []
last_updated: 2026-09-25
related: [[cricket-squad-chain]], [[cricket-pitch-data-chain]]
---

# Static Seed

Local JSON reader bundled with the package. Always enabled, no credentials, no network — it is the last source for squad data and the sole source for pitch data, subject to the requested team or venue existing in the seed.

## Where the data lives

`src/sportiq/cricket/data/` — ships with the package.

- `squads.json` — generated seed with 10 IPL and 9 international squads.
- `venues.json` — Phase 2 seed (added in commit log on 2026-05-28).

### squads.json coverage

IPL franchises: `CSK, MI, RCB, KKR, RR, DC, PBKS, SRH, LSG, GT` (10 teams, player records with `name / role / credits`).

Internationals: `IND, AUS, ENG, NZ, SA, PAK, SL, WI, BAN` (9 teams).

Roles are `BAT`, `BOWL`, `ALL`, `WK-BAT`.

### venues.json coverage

~14 IPL venues with `{name, city, pitch_type (batting/bowling/balanced), avg_first_innings, avg_chasing, boundary_size_m}`. Used by [[cricket-pitch-data-chain]] and the venue lookup inside [[cricket-build-dream11-team]].

## When it serves

- `StaticSeedSquadAdapter` is the final adapter in [[cricket-squad-chain]]. Whenever upstreams (cricapi) fail, this serves.
- `StaticSeedVenueAdapter` is the *only* adapter in [[cricket-pitch-data-chain]] for Phase 2.

The bundled JSON provides offline fallback in a healthy installation. An unknown venue returns `NotFoundError`; a missing or corrupt data file can still fail.

## Adapter behaviour

- Constructor never raises.
- `healthcheck()` returns `True` iff the bundled JSON file is present on disk.
- `StaticSeedSquadAdapter.fetch(team=...)` returns the normalised `{"players": [...], "team": ..., "source": "static_seed"}` shape (every player carries its `team`). Lookup is case-insensitive.
- `StaticSeedSquadAdapter.fetch()` with no `team` returns `{"squads": {...}, "source": "static_seed"}` — all teams.
- `StaticSeedVenueAdapter.fetch(venue=...)` returns the venues.json record + `{"key", "source"}`. Lookup is case-insensitive and tolerates the key, full name, or city. Raises `NotFoundError` on miss.
