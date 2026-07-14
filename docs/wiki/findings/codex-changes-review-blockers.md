---
title: codex_changes Review — Four Confirmed Merge Blockers
type: finding
tags: [review, http, middleware, football, tiebreakers, ratelimit, cache, security]
sources: [chat]
last_updated: 2026-07-14
related: [[0012-hosted-abuse-controls]], [[group-sim]], [[bracket-sim]], [[football-simulate-group]], [[football-simulate-bracket]]
---

# codex_changes Review — Four Confirmed Merge Blockers

A recall-biased line-by-line review (2026-07-14) of the 13-commit `codex_changes` hardening
branch found four confirmed defects that blocked merging into `main`, despite the full 758-test
suite passing. Two were proven with executable repros; two were verified against external
authoritative sources. All four blockers and the adjacent mid-body disconnect defect were fixed
on `codex_changes`, re-verified (766 tests, ruff, hook regression), and the branch was
fast-forward merged into `main` at `07dcf99` on 2026-07-14 (docs commit `50530ef`), pushed to
origin, and canary-deployed to Cloud Run as revision `sportiq-mcp-00035-vam` (100% traffic) after
verifying the SSE fix live on the tagged URL.

## Resolution

- `1f29e84` (`fix(core): preserve SSE after request body replay`) delegates to the real ASGI
  receive after replay, preserves all SSE chunks, and returns silently on mid-body disconnect.
- `18b42a6` (`fix(football): use head-to-head goals in group tiebreaks`) corrects the shared
  ranking tuple, locked-result regressions, and every directly affected model/skill description.
- `f7e30f3` (`fix(core): trust Cloud Run's rightmost forwarded IP`) closes spoofed-prefix bucket
  rotation and corrects the hosted trust-boundary documentation.
- `af3be73` (`fix(core): recover legacy counter values on increment`) resets and retries only
  diskcache `TypeError` and Redis `ResponseError`; connection failures still downgrade normally.

## 1. Request-limit middleware aborts every hosted SSE response (critical)

`core/request_limits.py` buffers the POST body and replays it via a fabricated `receive`
that returns `{"type": "http.disconnect"}` on its **second** call. MCP streamable-HTTP
defaults to SSE responses (`json_response=False`), and `sse-starlette`'s
`_listen_for_disconnect` makes exactly that second call — so it sees an instant "client
disconnected" and cancels the stream. Repro: an `EventSourceResponse` behind the middleware
delivered 0 of 3 chunks (3/3 without it). Every hosted `POST /mcp` tool call would return an
empty body. **Fix:** after the replay message, delegate to the original `receive` (it blocks
until a real disconnect). **Lesson (compounds the BaseHTTPMiddleware gotcha):** any `/mcp`
middleware that synthesises receive/send messages must be validated against a *streaming*
endpoint, not an echo app — unit tests with plain request/response apps cannot catch this
class of bug.

## 2. FIFA tiebreak criterion 3 uses overall goals instead of head-to-head goals

`football/models/group_sim.py:_rank_group` sorts equal-points cohorts by
`(h2h_points, h2h_gd, gf_overall, overall_gd, overall_gf)`. The official WC 2026 order is
h2h points → h2h GD → **h2h goals scored** → overall GD → overall GF. The code computes
`h2h_gf` but never uses it in the key, and the misplaced `gf` also ranks overall GF *above*
overall GD. Concrete failure: two teams tied on points that drew head-to-head — X (GF 5,
GD 0) vs Y (GF 4, GD +3) — FIFA ranks Y first; the code ranks X first. The wrong order was
also written into both `monte-carlo-bracket` SKILL.md copies, so docs and code were
self-consistently wrong. **Fix:** slot 3 → `h2h_gf`; correct the skill docs; note the known
approximation that h2h criteria are applied once per cohort, not re-applied iteratively.

## 3. Per-client rate-limit identity trusts the spoofable first X-Forwarded-For hop

`core/request_limits.py:_client_identity` takes `forwarded.split(",", 1)[0]`. On Cloud Run
only the **last** XFF entry (appended by Google's front end) is trustworthy; earlier entries
are client-supplied. An attacker rotates a fake first entry per request to mint fresh rate
buckets, fully bypassing the per-client 60/min cap (the global cap still holds). **Fix:**
take the last entry (`rsplit(",", 1)[-1]`), keep the `ipaddress` validation and the
`scope["client"]` fallback.

## 4. Legacy JSON-wrapped counters crash the new atomic `incr_counter`

Pre-branch `ratelimit.consume()` stored counters as JSON strings (`{"value": n, ...}`); the
branch's `cache.incr_counter` does a raw increment on the same keys. On diskcache this raises
`TypeError` (repro'd) — and since `consume()` runs *outside* the chain's per-adapter
try/except, the first budgeted fetch after upgrading crashes the tool with no envelope until
the old key expires (day buckets: 48 h TTL). On Redis the Lua INCR error is swallowed by
`_downgrade_to_disk`, silently and permanently downgrading the backend. **Fix:** reset and retry
only on diskcache `TypeError` or Redis `ResponseError`; genuine Redis connection failures retain
the normal downgrade path. The worst case is that one legacy window's count resets. **Lesson:**
changing a cache key's value *format* is a migration — check what the old code left behind under
the same keys.

## Deferred findings

- GET/DELETE `/mcp` are not rate-limited at all (SSE connection-exhaustion path remains open).
- `group_sim.simulate_group` is now production-dead (tests only).
- `football_simulate_group` now runs all 12 groups per call (~12× compute; deliberate, for
  contextual best-third probabilities).

## Review-method notes

What worked: reading the full diff line-by-line, then *verifying* each candidate empirically
(two repro scripts) or against primary sources, refuted 4 plausible-looking candidates
(`GROUP_STAGE` tokenisation, `NotFoundError.attempts`, redirect-loop bound, 12-group
`ValueError` reachability) and confirmed the real four. What didn't: the branch's own 758
green tests — all four blockers sat behind gaps in test *realism* (echo apps instead of SSE,
no legacy-format cache seeds, no spoofed-XFF case, tiebreak tests mirroring the same wrong
order as the code).
