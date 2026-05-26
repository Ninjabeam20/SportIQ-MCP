---
title: cricket_get_schedule
type: tool
tags: [cricket, schedule, fixtures]
sources: []
last_updated: 2026-05-26
related: [[cricket-fixtures-chain]], [[cricapi]]
---

# cricket_get_schedule

Returns upcoming match schedule, optionally filtered by series.

## Signature

```python
async def cricket_get_schedule(series_id: str | None = None) -> dict
```

`series_id` is optional. Off-season returns `data.matches = []`, not an error.

## Chain

[[cricket-fixtures-chain]]
