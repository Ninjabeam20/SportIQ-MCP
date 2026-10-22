---
title: Cricket Squad Chain
type: chain
tags: [cricket, squad, roster]
sources: []
last_updated: 2026-10-22
related: [[cricapi]], [[static-seed]], [[cricsheet]], [[cricket-build-dream11-team]]
---

# Cricket Squad Chain

`FallbackChain` that powers `cricket_get_squad`. Always terminates in `static_seed` so there is always a last-resort response.

## Resolution order

`cricapi` → `static_seed`

`static_seed` is always enabled and serves IPL 2026 rosters from `src/sportiq/cricket/data/squads.json`,
generated from [[cricsheet]] by `scripts/build_cricket_squads.py`. Team input may be a code (`MI`) or the
official franchise name (`Mumbai Indians`); there is no substring matching. The tools pass `series_id`
through from match resolution, so a CricAPI squad is fetched for the right series.

## TTLs

- Fresh: 12h
- Stale ceiling: 3d

## Cache key

`sportiq:cricket:squad:{team_hash}:{series_id_hash}` — each value (`team`/`all`, `series_id`/`none`) is lowercased and hashed with an 8-byte BLAKE2s digest.
