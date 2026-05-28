---
title: cricket_player_form_index
type: tool
tags: [cricket, form, stats]
sources: []
last_updated: 2026-05-28
related: [[form-index]], [[cricket-player-stats-chain]]
---

# cricket_player_form_index

Returns a 0-100 form score for a player, derived from the player_stats chain output.

## Signature

```python
async def cricket_player_form_index(player_id: str) -> dict
```

`player_id` is the upstream identifier (CricAPI player ID, or Cricbuzz numeric ID).

## What goes in

[[cricket-player-stats-chain]] returns either the CricAPI `/v1/players_info` payload or the RapidAPI Cricbuzz `/stats/v1/player/{id}/career` payload. The tool extracts T20I career average + strike rate from whichever served — see `_t20_career_numbers()` in `intel_tools.py`.

Phase 2 has no per-innings recent stream; the form model falls back to the career baseline. Recent-innings ingestion is a follow-up. `samples=0` is therefore expected and normal in Phase 2 — it does not indicate a data error.

## Returns

```json
{
  "data": {
    "form_score": 64.0,
    "trend": "stable",
    "samples": 0,
    "player_id": "p_kohli_001",
    "career_avg": 51.39,
    "career_sr": 137.96
  },
  "meta": {"source": "cricapi", "is_stale": false, "estimated": true}
}
```
