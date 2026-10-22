---
title: Static Seed
type: data-source
tags: [cricket, squad, pitch, static]
sources: [src/sportiq/cricket/adapters/static_seed.py, scripts/build_cricket_squads.py, scripts/build_cricket_priors.py]
last_updated: 2026-10-22
related: [[cricket-squad-chain]], [[cricket-pitch-data-chain]], [[cricsheet]], [[football-squad-chain]]
---

# Static Seed

Local JSON reader bundled with the package. Always enabled, no credentials, no network — it is the last source for squad data and the sole source for pitch data, subject to the requested team or venue existing in the seed.

## Where the data lives

`src/sportiq/cricket/data/` — ships with the package.

- `squads.json` — generated from [[cricsheet]] by `scripts/build_cricket_squads.py` (2026-10-22).
- `venues.json` — generated from [[cricsheet]] by `scripts/build_cricket_priors.py`.

Both are regenerated, never hand-edited. Football ships **no** squads (see [[football-squad-chain]]).

### squads.json coverage

A top-level `_meta` block (`source`, `season`, `generated_at`, `script`, `credits_source: "formula"`,
`roles_source`, `note`), then the 10 IPL franchises `CSK, DC, GT, KKR, LSG, MI, PBKS, RCB, RR, SRH`:
203 players, each `{name, player_id, role, credits}`. A franchise's squad is every player who appeared for
it in IPL 2026; 2027 retentions are not reflected. `player_id` is the Cricsheet registry id and names are
Cricsheet scorecard names (`"V Kohli"`).

- **Roles** (`BAT`, `BOWL`, `ALL`, `WK-BAT`) are inferred from season appearances, not official.
  `WK-BAT` needs a stumping (Cricsheet has no keeper field), so some keepers read as `BAT`. Shortfalls
  are reported, not hand-fixed: LSG has no `WK-BAT`, and LSG/DC/GT/RCB have no `ALL`, so a Dream11 XI
  between two of those four is infeasible and returns the solver's role-shortfall reason.
- **Credits** are a heuristic: impact = runs + 20 × wickets, mapped linearly to 7.0–11.0 in 0.5 steps.

The former 9 national-team squads were dropped with the hand-written seed.

### venues.json coverage

16 IPL venues with `{name, city, pitch_type (batting/bowling/balanced), avg_first_innings, avg_chasing,
boundary_size_m}`, including Mullanpur and Raipur (added 2026-10-22 from the script's documented
`NEW_VENUES` rule table). Used by [[cricket-pitch-data-chain]] and the venue lookup inside
[[cricket-build-dream11-team]].

## When it serves

- `StaticSeedSquadAdapter` is the final adapter in [[cricket-squad-chain]]. Whenever upstreams (cricapi) fail, this serves.
- `StaticSeedVenueAdapter` is the *only* adapter in [[cricket-pitch-data-chain]] for Phase 2.

The bundled JSON provides offline fallback in a healthy installation. An unknown venue returns `NotFoundError`; a missing or corrupt data file can still fail.

## Adapter behaviour

- Constructor never raises.
- `healthcheck()` returns `True` iff the bundled JSON file is present on disk.
- `StaticSeedSquadAdapter.fetch(team=...)` returns the normalised `{"players": [...], "team": ..., "source": "static_seed"}` shape (every player carries its `team`). The team may be a code or the official franchise name (`cricket/teams.py`), case-insensitive. An unknown team gets an empty player list here; the cricket intel tools turn that into a `NOT_FOUND` listing the known team codes. `_meta` is never treated as a team.
- `StaticSeedSquadAdapter.fetch()` with no `team` returns `{"squads": {...}, "source": "static_seed"}` — all teams.
- `StaticSeedVenueAdapter.fetch(venue=...)` returns the venues.json record + `{"key", "source"}`. Lookup is case-insensitive and tolerates the key, full name, or city, and also provider strings such as `"Wankhede Stadium, Mumbai"`. Raises `NotFoundError` listing the known venues on a miss.
