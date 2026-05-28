---
title: Form Index
type: model
tags: [cricket, form, t20]
sources: []
last_updated: 2026-05-28
related: [[cricket-player-form-index]], [[cricket-player-stats-chain]], [[captain-score]]
---

# Form Index

Pure function `compute_form_index(recent_innings, career_avg, career_sr) -> dict` returning a 0-100 score plus a `rising | stable | falling` trend.

## How it composes

- Each recent innings is reduced to a single score (`_innings_score`) combining runs, strike-rate bonus, and a small bowling credit per wicket.
- The last 5 innings are blended with exponential weights `(0.40, 0.25, 0.15, 0.12, 0.08)` (sum = 1.0) so the newest innings dominates but older form still nudges.
- A career baseline is computed from average + strike rate, clamped into 0-100.
- Final score = 0.7 × weighted recent + 0.3 × career baseline, clamped 0..100.

## Trend

Latest innings vs the median of innings 2..N within the 5-innings window. > 120% of median ⇒ `rising`; < 80% ⇒ `falling`; otherwise `stable`.

## Phase 2 limitation

The cricket player_stats chain currently delivers only career numbers — no per-innings recent stream. So [[cricket-player-form-index]] passes `recent_innings=[]` and the model falls back fully to the career baseline. Recent-innings ingestion is a follow-up; the model shape is ready for it the day the data lands.
