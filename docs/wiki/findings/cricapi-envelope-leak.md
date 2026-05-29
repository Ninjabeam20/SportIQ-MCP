---
title: CricAPI envelope leak + failure-as-success
type: finding
tags: [cricket, cricapi, security, fallback]
sources: [2026-05-30-step8-live-findings.md, cricapi]
last_updated: 2026-05-30
related: [[cricapi]], [[cricket-scorecard-chain]], [[cricket-squad-chain]], [[project-not-found-invariant]]
---

# CricAPI envelope leak + failure-as-success

The step8 live testing pass found that three CricAPI adapters returned the **raw**
upstream response instead of unwrapping it, which both leaked the request API key
and let a failure response masquerade as a successful empty payload.

## What happened

CricAPI wraps every response as `{apikey, status, data?, reason?}` and **echoes the
request `apikey` back** in the body. On failure it sets `status: "failure"`, omits
`data`, and fills `reason` (e.g. `"ERR: Scorecard <id> not found"`).

`CricAPIScorecardAdapter`, `CricAPIPointsTableAdapter`, and `CricAPIPlayerInfoAdapter`
did `return await get_json(...)` — the raw envelope. Consequences:

1. 🔴 **Key leak.** The request `apikey` flowed straight into the tool's `{data}`
   envelope and out to the model/caller.
2. 🔴 **Failure-as-success.** A `status: "failure"` body was returned as a successful
   result (no exception), so the tool emitted a `{data, meta}` success envelope
   wrapping an error payload.
3. 🟠 **Squad seed shadowing.** `CricAPISquadAdapter` was reachable with `series_id=None`
   (the squad chain passes `series_id` through, `None` for team-only lookups). It then
   queried `series_squad?id=None`, got a failure that normalised to **0 players**, and
   the chain cached that empty "success" — permanently shadowing the 11-player
   `static_seed` roster.

## Fix

`cricapi.py` gained a `_unwrap(resp)` helper: raise `NotFoundError(reason)` when
`status != "success"`, else return the inner `data` (apikey/status/info stripped).
Scorecard / points-table / player-info call it. The squad adapter raises
`NotFoundError` when `series_id` is falsy (so the chain falls through to the
`static_seed` terminator) and validates `status` before normalising.

`cricket_get_scorecard` and `cricket_get_points_table` now also catch `NotFoundError`
→ `NOT_FOUND` envelope (these chains have no terminator, unlike squad). See
[[project-not-found-invariant]].

## Regression coverage

- `tests/adapters/test_cricapi.py`: scorecard raises `NotFoundError` on the failure
  fixture; `apikey` absent from scorecard/points-table/player-info output; squad raises
  without a `series_id`. Fixture: `tests/fixtures/cricapi/match_scorecard_failure.json`.
- `tests/tools/test_cricket_raw_tools.py`: scorecard/points-table `NOT_FOUND` envelopes;
  `cricket_get_squad` unknown team → `static_seed` (no raise).

## Note (not a bug)

Live, `cricket_get_scorecard` / `cricket_get_points_table` now return
`ALL_SOURCES_FAILED`: CricAPI's free tier does not serve those endpoints and the paid
RapidAPI escape-hatch is unsubscribed. The envelope is honest; this is a data-access
limitation, not a defect.
