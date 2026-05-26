---
title: cricket_get_points_table
type: tool
tags: [cricket, standings, points-table]
sources: []
last_updated: 2026-05-26
related: [[cricket-standings-chain]], [[cricapi]]
---

# cricket_get_points_table

Returns the points table / standings for a cricket series.

## Signature

```python
async def cricket_get_points_table(series_id: str) -> dict
```

`series_id` required. Returns `INVALID_INPUT` if empty.

## Chain

[[cricket-standings-chain]]
