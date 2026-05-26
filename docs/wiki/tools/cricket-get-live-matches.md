---
title: cricket_get_live_matches
type: tool
tags: [cricket, live-scores]
sources: []
last_updated: 2026-05-26
related: [[cricket-live-score-chain]], [[cricapi]]
---

# cricket_get_live_matches

Returns all currently live cricket matches across all series.

## Signature

```python
async def cricket_get_live_matches() -> dict
```

No parameters. Returns `{data, meta}` envelope or `{error}` envelope.

## Success response

```json
{
  "data": {"matches": [{"id": "abc123", "name": "India vs Australia", ...}]},
  "meta": {"source": "cricapi", "is_stale": false, "duration_ms": 187}
}
```

Off-season: `data.matches` is an empty list — not an error.

## Chain

[[cricket-live-score-chain]]
