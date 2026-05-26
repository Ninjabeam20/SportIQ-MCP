---
title: cricket_get_scorecard
type: tool
tags: [cricket, scorecard]
sources: []
last_updated: 2026-05-26
related: [[cricket-live-score-chain]], [[cricapi]]
---

# cricket_get_scorecard

Returns the full scorecard for a specific match.

## Signature

```python
async def cricket_get_scorecard(match_id: str) -> dict
```

`match_id` is from `cricket_get_live_matches` or `cricket_get_schedule`.

## Chain

[[cricket-live-score-chain]]
