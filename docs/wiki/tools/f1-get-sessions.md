---
title: f1_get_sessions
type: tool
tags: [f1, sessions]
sources: [src/sportiq/f1/tools.py]
last_updated: 2026-10-22
related: [[f1-sessions-chain]], [[openf1]], [[f1-predict-pit-strategy]]
---

# f1_get_sessions

Returns F1 sessions for a given year, optionally filtered by country.

## Signature

```python
async def f1_get_sessions(
    year: int,
    country: str | None = None,
    session_name: str | None = None,
    latest_completed: bool = False,
) -> Envelope
```

## Args
- `year` — Championship year (e.g. 2026). Must be 2018–2030.
- `country` — Optional country name filter (e.g. "Netherlands"); title-cased before it is sent.
- `session_name` — Optional exact session name, case-insensitive (`"Race"`, `"Qualifying"`, `"Sprint"`).
- `latest_completed` — When true, return only the session with the greatest `date_end` before now (UTC).
  With `session_name="Race"` this is the latest finished Grand Prix — the usual way to get a
  `session_key` for the analysis tools. Sessions with a missing or unparseable `date_end` are skipped.

Both filters run after the chain fetch, so the cache key stays `year` + `country`.

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
