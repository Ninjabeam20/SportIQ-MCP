---
title: Pitch Report
type: model
tags: [cricket, pitch, venue]
sources: []
last_updated: 2026-05-28
related: [[cricket-get-pitch-report]], [[cricket-pitch-data-chain]], [[captain-score]]
---

# Pitch Report

`pitch_report(venue_record) -> dict` summarises a venue into a fixture-friendliness profile that downstream tools can use.

## Inputs

A row from `venues.json` (delivered via [[cricket-pitch-data-chain]]). Required keys: `pitch_type` and `avg_first_innings`. Optional: `name`, `city`.

## Output

```json
{
  "batting_friendly": 0.78,
  "expected_first_inn": 178,
  "recommendation": "High-scoring deck — load up on top-order batters...",
  "venue": "Wankhede Stadium",
  "pitch_type": "batting"
}
```

## How `batting_friendly` is computed

```
base   = {batting: 0.78, balanced: 0.55, bowling: 0.32}[pitch_type]
shift  = clamp(-0.15..0.15, (avg_first_innings - 175) / 200)
result = clamp(0..1, base + shift)
```

A high-scoring batting deck (185 avg first innings) lands ~0.83; a low-scoring bowler-friendly track (155) lands ~0.22.

## Recommendation strings

Three buckets keyed off `batting_friendly`:

- ≥ 0.70 — "High-scoring deck — load up on top-order batters and finishers; fade specialist seamers in favour of wicket-taking spinners."
- ≤ 0.40 — "Bowler-friendly track — stack pace + wrist-spin wickets; trim the batting lineup to anchor types over hitters."
- otherwise — "Balanced pitch — pick top-order anchors plus a wicket-taker. No structural tilt; lean on form."

Tools may surface these strings verbatim.
