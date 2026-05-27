---
title: "ADR-0007: Cricket Fallback Strategy — Opt-in Scrapers + Paid Escape Hatch"
type: decision
tags: [cricket, scraper, fallback, tos]
sources: []
last_updated: 2026-05-27
related: [[cricapi]], [[ndtv-sports-scraper]], [[cricbuzz-scraper]], [[rapidapi-cricbuzz]], [[static-seed]]
---

# ADR-0007: Cricket Fallback Strategy — Opt-in Scrapers + Paid Escape Hatch

## Status

Accepted — 2026-05-26

## Context

Phase 1 requires five cricket RAW tools backed by reliable data. The options evaluated:

1. **CricAPI only** — 100 req/day cap is too low for production use under load.
2. **CricAPI + Cricbuzz scraper by default** — Cricbuzz ToS explicitly prohibits scraping. Shipping a ToS-violating adapter enabled by default exposes the package (and its users) to legal risk.
3. **CricAPI + NDTV Sports + opt-in scrapers + RapidAPI paid mirror** — Free legal primary (CricAPI + CricSheet), ToS-risky adapters opt-in, and one licensed paid escape hatch.

Option 3 was chosen.

## Decision

- **CricAPI**: primary for live scores, fixtures, standings, squad. 100 req/day; runs when `CRICAPI_KEY` is set.
- **NDTV Sports scraper**: opt-in via `SPORTIQ_ENABLE_NDTV=1`. Operator explicitly accepts any ToS risk.
- **Cricbuzz scraper**: opt-in via `SPORTIQ_ENABLE_CRICBUZZ=1`. Same posture.
- **RapidAPI Cricbuzz**: licensed paid mirror. Opt-in via `RAPIDAPI_KEY`. The escape hatch for operators who need reliable live data without scraper fragility.
- **Static seed** (`squads.json`): always-on terminator for squad chain. Ships with IPL 2026 rosters.

## Consequences

- Default install of the PyPI package has no scrapers enabled. `cricket_get_squad` always succeeds (static seed); other tools require at least one credential.
- Adapter constructors never raise. `healthcheck()` returns `False` and `fetch()` raises `MissingCredentialsError` when disabled/unconfigured. Chain walks past silently.
- `sportiq_health()` lists all adapters including disabled ones, giving operators a clear picture of what needs configuring.
- `static_seed.py` was pulled forward from Phase 2 to serve as the squad chain terminator. Phase 2 will add `venues.json` but does not need to re-create the adapter.

## 2026-05-27 Amendment — CricSheet dropped

`cricsheet.org/register/people.json` returned 404 at runtime (the live URL is `people.csv` now, and the CSV schema has no `teams` column, so `CricSheetSquadAdapter`'s team-filter logic was structurally unworkable). Both `CricSheetSquadAdapter` and `CricSheetPlayerStatsAdapter` are removed. The squad chain becomes `cricapi → static_seed`; player_stats data is deferred to Phase 3 (when Dream11 needs it, we'll source it through CricAPI or a paid mirror, not CricSheet).
