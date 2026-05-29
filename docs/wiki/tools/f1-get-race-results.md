---
title: f1_get_race_results
type: tool
tags: [f1, race-results]
sources: []
last_updated: 2026-05-29
related: [[f1-results-chain]], [[jolpica]]
---

# f1_get_race_results

Returns the final classification for one race — finishing order, times, grid, points, fastest laps — keyed by **year + round** from the Jolpica/Ergast `results.json` endpoint.

> Phase 3.1 rescope (audit finding #3): this tool previously took a `session_key` and returned the *drivers* list (a mislabeled stub — there was no results chain). It now takes `year` + `round` and serves real results via [[f1-results-chain]].

## Signature

```python
async def f1_get_race_results(year: int, round: int) -> dict
```

## Args
- `year` — Championship year (e.g. 2025). Must be 2018–2030.
- `round` — Round number within the season (1-based; e.g. 1 for the opener). Must be 1–30.

## Success response

```json
{
  "data": {"results": {"MRData": {"RaceTable": {"Races": [{"raceName": "...", "Results": [...]}]}}}},
  "meta": {"source": "jolpica", "is_stale": false}
}
```

`data.results` is the raw Ergast `RaceTable` payload.

## Chain

[[f1-results-chain]]
