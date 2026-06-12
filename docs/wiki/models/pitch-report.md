---
title: Pitch Report
type: model
tags: [cricket, pitch, venue]
sources: []
last_updated: 2026-06-12
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
shift  = clamp(-0.15..0.15, (avg_first_innings - LEAGUE_PAR) / 200)
result = clamp(0..1, base + shift)
```

`LEAGUE_PAR` is the **measured** league T20 par — mean first-innings total across
all in-window (2018+) Cricsheet IPL matches, derived and printed by
`scripts/build_cricket_priors.py`. Currently **178** (n=607,
`_LEAGUE_PAR_T20` in `cricket/models/pitch_report.py`). It replaced a hand-set 175
on 2026-06-12: the venues.json regeneration ([[cricsheet]]) lifted venue means to
~180+, so the stale centre read nearly every venue as batting-shifted. Recheck the
constant against the script's printout whenever venues.json is regenerated.

A high-scoring batting deck (188 avg first innings) lands ~0.83; a low-scoring bowler-friendly track (158) lands ~0.22.

## Recommendation strings

Three buckets keyed off `batting_friendly`:

- ≥ 0.70 — "High-scoring deck — load up on top-order batters and finishers; fade specialist seamers in favour of wicket-taking spinners."
- ≤ 0.40 — "Bowler-friendly track — stack pace + wrist-spin wickets; trim the batting lineup to anchor types over hitters."
- otherwise — "Balanced pitch — pick top-order anchors plus a wicket-taker. No structural tilt; lean on form."

Tools may surface these strings verbatim.
