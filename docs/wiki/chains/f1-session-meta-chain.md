---
title: F1 Session Meta Chain
type: chain
tags: [f1, openf1, sessions, circuits]
sources: [src/sportiq/f1/chains.py, src/sportiq/f1/intel_tools.py]
last_updated: 2026-10-22
related: [[openf1]], [[f1-sessions-chain]], [[f1-predict-pit-strategy]], [[f1db]], [[pit-strategy]]
---

# F1 Session Meta Chain

`FallbackChain` that resolves one OpenF1 session by `session_key`, used to recover the session's `circuit_key` so pit-strategy tools can apply that circuit's measured pit-lane loss.

## Resolution order
[[openf1]] sessions endpoint (only source) → stale cache.

## TTLs
- Fresh: 6h
- Stale ceiling: 24h

A session's metadata does not change once it exists, so it uses the calendar-listing class.

## Cache key
`sportiq:f1:session_meta:{session_key}`

## Consumers
`f1/intel_tools.py` `_resolve_circuit_profile(session_key)` fetches the session, reads `circuit_key`, and
maps it to the F1DB-derived profile in `f1/data/circuits.json` ([[f1db]]). It is best-effort enrichment:
`AllSourcesFailedError`, `NotFoundError` (an unknown `session_key`; OpenF1's 404 "No results found" is
mapped to `NotFoundError`) or an unknown circuit all return `None`, and the caller falls back to the
generic pit-loss default instead of failing the tool.
