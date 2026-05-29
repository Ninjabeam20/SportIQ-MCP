---
title: Elo Ratings
type: model
tags: [football, elo]
sources: []
last_updated: 2026-05-29
related: [[poisson-xg]], [[bracket-sim]], [[football-groups-chain]]
---

# Elo Ratings

Standard Elo helpers seeding the Poisson engine when per-team scoring rates are thin (always, for a pre-tournament WC).

- `expected_score(rating_a, rating_b, home_advantage)` — logistic win-expectation `1 / (1 + 10^(-((Ra+H)-Rb)/400))`.
- `update_rating(rating, expected, actual, k=30)` — post-match rating.

Seed ratings ship in `football/data/elo_seed.json` (48 teams) and are served via [[football-groups-chain]]. Used for the knockout-shootout coin flip in [[bracket-sim]].
