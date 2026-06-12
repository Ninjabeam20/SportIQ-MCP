---
title: Cricsheet
type: data-source
tags: [cricket, ipl, venues, offline-seed, calibration]
sources: [cricsheet]
last_updated: 2026-06-11
related: [[cricket-get-pitch-report]], [[pitch-report]], [[venues]]
---

# Cricsheet

Free ball-by-ball IPL match data (2008–present, JSON) used **offline only** to
derive measured venue scoring priors. No runtime dependency and no adapter —
Cricsheet never ships in the package and is never fetched live. (The earlier
Cricsheet *live adapter* was dropped in `9a37236` for a structural mismatch; this
is a different, offline-aggregation usage.)

## License

Cricsheet's match data carries **no explicit license** ("freely-available
structured data"; the separate Register dataset is ODC-By 1.0). Posture, matching
hundreds of public projects built on Cricsheet:

- We ship only **derived aggregates** (facts/statistics — venue averages), never
  the raw match database.
- We **attribute Cricsheet prominently** in the README "Data sources & credits".
- If Cricsheet ever publishes explicit terms we comply or regenerate from another
  source.

## Source

- Downloads: `https://cricsheet.org/downloads/` (`ipl_json.zip`).
- Extracted to `datasets/ipl_json/` (gitignored) on the dev machine only.

## What we derive

`scripts/build_cricket_priors.py` reads the per-match JSON and regenerates the
committed seed `src/sportiq/cricket/data/venues.json` (same schema as before):

| Field | Source | Notes |
| :--- | :--- | :--- |
| `avg_first_innings` | mean 1st-innings total | seasons 2018+, venues with ≥12 matches in-window |
| `avg_chasing` | mean 2nd-innings total | chases ending early pull this below the 1st-innings mean |
| `pitch_type` | **preserved hand-set label** | qualitative; not relabeled from absolute averages (see below) |
| `boundary_size_m`, `name`, `city` | **preserved** | not present in Cricsheet |

Regen lifted most grounds (e.g. Eden Gardens 168→188, Kotla 172→186) — modern IPL
scoring runs higher than the old eyeballed seeds. Four thin-sample venues
(`dharamshala`, `visakhapatnam`, `guwahati`, `indore`, all <12 in-window matches)
keep their hand-set numbers rather than adopt a noisy small-sample mean.

### Why `pitch_type` is preserved, not measured

League-wide scoring inflation pushes every venue's absolute average up, so an
absolute-threshold relabel (e.g. "batting if avg ≥ 185") would flip grounds for a
trend that isn't venue-specific. The qualitative label is left as a hand-set
judgment; the measured `avg_first_innings` already feeds `pitch_report`'s
`_avg_factor` for the numeric tilt. Revisit if a future phase needs a relative
(vs-league) tilt classification.

## Deliberately NOT derived (yet)

- **`matchups.json` (batter-vs-bowler H2H)** — blocked on name reconciliation.
  Cricsheet uses scorecard initials ("AD Russell"); `squads.json` uses mixed full
  names ("Andre Russell"). Only ~13% (25/194) match exactly, and surname+initial
  fuzzy matching mis-maps common Indian names. A clean join would need a
  hand-curated alias table, which conflicts with the project's "no hand-curated
  player-history data" constraint. Deferred pending a decision on that trade-off.
- **Win-model logistic calibration** — its own gated phase (reliability curve must
  be shown before `cricket_find_value_bets` goes live).

## Regeneration cadence

Re-run the build script after each IPL season (venue norms drift slowly). The
venue alias table (Cricsheet name substrings → canonical key) is explicit in the
script; new grounds joining the calendar must be added there.
