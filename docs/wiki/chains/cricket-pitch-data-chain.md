---
title: Cricket Pitch Data Chain
type: chain
tags: [cricket, pitch, venue, static]
sources: []
last_updated: 2026-05-28
related: [[static-seed]], [[cricket-get-pitch-report]], [[pitch-report]]
---

# Cricket Pitch Data Chain

`FallbackChain` powering [[cricket-get-pitch-report]] and the venue lookup inside [[cricket-build-dream11-team]]. v1 is offline-only — `static_seed` is the sole adapter.

## Resolution order

`static_venue` (terminator only)

The chain is designed to absorb a future "recent scorecards at this venue" adapter that would adjust friendliness based on the last N matches played there. Until that adapter exists, the static seed is authoritative.

## TTLs

- Fresh: 1 year (`31_536_000`s) — venue characteristics don't change.
- Stale ceiling: 0 — no point holding stale of a never-changing source.

## Cache key

`sportiq:cricket:pitch:{venue_slug}` where `venue_slug = venue.lower().replace(' ', '_')`.

Per-venue keying means one query primes the cache for all subsequent lookups of the same venue, regardless of capitalisation or input form (`Wankhede`, `wankhede`, `Wankhede Stadium` all hash to the same key after normalisation in the adapter).
