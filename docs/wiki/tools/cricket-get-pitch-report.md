---
title: cricket_get_pitch_report
type: tool
tags: [cricket, pitch, venue]
sources: []
last_updated: 2026-05-28
related: [[pitch-report]], [[cricket-pitch-data-chain]], [[static-seed]]
---

# cricket_get_pitch_report

Summarises pitch characteristics for a venue — batting-friendliness, expected first-innings total, and a short recommendation an AI can quote.

## Signature

```python
async def cricket_get_pitch_report(venue: str) -> dict
```

`venue` accepts a `venues.json` key (`wankhede`), the official stadium name (`Wankhede Stadium`), or the city (`Mumbai`). Matching is case-insensitive.

## Returns

```json
{
  "data": {
    "batting_friendly": 0.797,
    "expected_first_inn": 178,
    "recommendation": "High-scoring deck — load up on top-order batters...",
    "venue": "Wankhede Stadium",
    "pitch_type": "batting"
  },
  "meta": {"source": "static_seed", "is_stale": false, ...}
}
```

## Behavior

- `pitch_type` is one of `batting`, `bowling`, `balanced` (from venues.json).
- `batting_friendly` blends the pitch type with a centred shift around the average first-innings total — 175 is the par.
- `recommendation` is a short prose string the model is free to surface to the user verbatim.

## Phase 2 limitations

The chain has only the `static_seed` terminator (offline-only). Recent-match enrichment from the [[cricket-scorecard-chain]] is a follow-up so freshly resurfaced pitches (e.g. relays in IPL playoffs) can shift the friendliness score.
