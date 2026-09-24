---
title: cricket_get_scorecard
type: tool
tags: [cricket, scorecard]
sources: []
last_updated: 2026-09-25
related: [[cricket-scorecard-chain]], [[cricapi]]
---

# cricket_get_scorecard

Returns the full scorecard for a specific match.

## Signature

```python
async def cricket_get_scorecard(match_id: str) -> dict
```

`match_id` is from `cricket_get_live_matches` or `cricket_get_schedule`.

## Chain

[[cricket-scorecard-chain]] uses a cache key per match ID.
