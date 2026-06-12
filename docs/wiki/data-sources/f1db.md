---
title: F1DB
type: data-source
tags: [f1, circuits, pit-stops, offline-seed, calibration]
sources: [f1db]
last_updated: 2026-06-12
related: [[undercut]], [[pit-strategy]], [[f1-undercut-window]], [[f1-predict-pit-strategy]]
---

# F1DB

Free, comprehensive Formula 1 database (1950–present) used **offline only** to
derive measured per-circuit pit-loss and stop profiles. No runtime dependency and
no adapter — F1DB never ships in the package and is never fetched live.

## License

**CC BY 4.0** — commercial use allowed, attribution required. The credit lives in
the README "Data sources & credits" section (link + license). This is a hard
obligation, not courtesy.

## Source

- Repo / releases: `https://github.com/f1db/f1db` (CSV release `f1db-csv.zip`).
- Downloaded to `datasets/` (gitignored) on the dev machine only.

## What we derive

`scripts/build_f1_circuit_profiles.py` reads the F1DB CSVs **plus OpenF1 lap data**
(cached under `datasets/openf1/`) and writes the committed seed
`src/sportiq/f1/data/circuits.json` (~24 circuits, few KB), keyed by OpenF1
`circuit_key`:

| Field | Source | Notes |
| :--- | :--- | :--- |
| `pit_loss_s` | OpenF1 laps: median of `in_lap + out_lap − 2 × baseline` per stop | baseline = median of the driver's fastest-half green-flag laps (SC/VSC-robust); per-stop losses filtered to an 8–45s band; seasons 2023–2024 (+2025 where OpenF1 still serves it keyless) |
| `typical_stops` | F1DB: median stops per driver per race | seasons 2022–2025 at that circuit |
| `lap_length_km` | `f1db-circuits.length` | |
| `sample_size` | n in-band loss samples behind the median | sanity / confidence (min 20 enforced) |

Measured range is ~20.5s (Monte Carlo, the lowest — matches the known real-world
ordering) to ~31.9s (Silverstone) — versus the old flat hardcoded `22.0s`.

**Why not F1DB pit-stop times for `pit_loss_s`:** F1DB `timeMillis` is pit-lane
*transit* time (entry line → exit line), not time *lost* vs staying out. Transit
overestimates loss by the bypass-section time and inverts orderings (Monaco transit
24.8s > Spa 23.3s, but Monaco LOSS is among the lowest). The undercut model adds
`pit_loss_s` to the gap, so it must be the loss quantity — hence the OpenF1
lap-based measurement.

**OpenF1 access note (2026-06):** recent-season data (2025+) returns 401 without an
API key; the build script skips paywalled sessions with a warning and works from
the free historical seasons. Responses are cached in `datasets/openf1/` so re-runs
are offline.

## How it reaches the tools

Keyed by OpenF1 `circuit_key`, so at runtime the resolver is an exact integer
lookup: a session payload already carries `circuit_key` → the `f1:session_meta` chain
(`f1_session_meta_chain`) → `circuits.py:profile_for_circuit_key` → profile. Unknown circuit → `None` and the
tools fall back to the 22.0s default with `meta.circuit_profile: false`. Models stay
I/O-free: the resolved `pit_loss_s` is passed in as an argument. Consumers:
[[f1-undercut-window]] and [[f1-predict-pit-strategy]].

## Regeneration cadence

Re-run the build script after calendar changes (annually is enough). The pit-stop
join is `pit-stops → races → circuits`; the F1DB→OpenF1 alias table is explicit in
the script and fails loud on any current-calendar circuit it cannot map.
