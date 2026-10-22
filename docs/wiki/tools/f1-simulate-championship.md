---
title: f1_simulate_championship
type: tool
tags: [f1, championship, monte-carlo, intel]
sources: [jolpica]
last_updated: 2026-10-22
related: [[championship-sim]], [[f1-standings-chain]], [[f1-get-standings]]
---

# f1_simulate_championship

Estimates each driver's F1 drivers' title probability for the rest of a season: a Monte Carlo over the remaining races and sprints, plus exact elimination maths.

## Signature

```python
async def f1_simulate_championship(
    year: int = 2026,
    iterations: int = 10000,   # clamped to 1000–20000
    seed: int | None = None,
) -> Envelope
```

## Data flow

1. `f1_standings_chain` (Jolpica → FastF1, normalised shape) and `f1_schedule_chain` (Jolpica `/{year}.json`, static schedule TTL 6 h / 24 h), fetched concurrently.
2. Remaining rounds = rounds dated after the standings' last completed round (sprint flag from the Jolpica `Sprint` key).
3. [[championship-sim]] runs off the event loop (`asyncio.to_thread`). It is in `_EXPENSIVE_TOOLS`, so it shares the expensive-tool semaphore and the tool deadline.

## Output

- `data.drivers`: `{code, points_now, title_prob, expected_points, eliminated, max_possible}`, sorted by `title_prob`.
- `data.max_remaining_points`, `data.rounds_remaining`.
- `meta.estimated = true`, `meta.model = "plackett-luce-points-rate"`, `meta.iterations`, `meta.rounds_completed`, plus `staleness_meta(standings, schedule)`.

## Errors

- `INVALID_INPUT`: year outside 2018–2030, or seed out of range.
- `ALL_SOURCES_FAILED` / `NOT_FOUND`: standings or schedule unavailable; `NOT_FOUND` also when the season has no driver standings yet.

## Caveats

- Drivers' title only; constructors are not simulated.
- A round whose sprint has run but whose GP has not is counted as completed, because standings carry one round number.
- Strength is the season points rate, so it does not model car upgrades or form swings.
