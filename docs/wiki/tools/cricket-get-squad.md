---
title: cricket_get_squad
type: tool
tags: [cricket, squad, roster]
sources: []
last_updated: 2026-05-26
related: [[cricket-squad-chain]], [[cricapi]], [[cricsheet]], [[static-seed]]
---

# cricket_get_squad

Returns squad roster for a cricket team. Always succeeds because `static_seed` is the chain terminator.

## Signature

```python
async def cricket_get_squad(team: str, series_id: str | None = None) -> dict
```

`team` accepts IPL codes (`MI`, `CSK`, etc.) or national codes (`IND`, `AUS`).
`series_id` optional — used for tournament-specific squads via CricAPI.

## Chain

[[cricket-squad-chain]]
