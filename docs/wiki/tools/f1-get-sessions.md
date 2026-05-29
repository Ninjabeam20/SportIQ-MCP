---
title: f1_get_sessions
type: tool
tags: [f1, sessions]
sources: []
last_updated: 2026-05-29
related: [[f1-sessions-chain]], [[openf1]]
---

# f1_get_sessions

Returns F1 sessions for a given year, optionally filtered by country.

## Signature

```python
async def f1_get_sessions(year: int, country: str | None = None) -> dict
```

## Args
- `year` — Championship year (e.g. 2025). Must be 2018–2030.
- `country` — Optional country name filter (e.g. "Monaco").

## Success response

```json
{
  "data": {"sessions": [{"session_key": 9877, "session_type": "Race", "date_start": "..."}]},
  "meta": {"source": "openf1", "is_stale": false}
}
```

Off-season or no results: `data.sessions` is an empty list — not an error.

## Chain

[[f1-sessions-chain]] — **OpenF1-only.** Jolpica was wired as a fallback but its results endpoint has a different signature (requires `round`) and output shape (`results`, not `sessions`), so it raised on every attempt (audit finding #2). Removed in Phase 3.1.
