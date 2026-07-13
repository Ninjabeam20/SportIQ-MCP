# Codex Changes Hardening and Football Correctness Design

**Status:** Approved for implementation
**Date:** 2026-07-14
**Branch:** `codex_changes`

## Goal

Complete five ordered batches: repair the agent hooks, correct public security claims,
add hosted abuse controls, close the scoped backend contract defects, and correct the
known World Cup group/fixture behavior. Preserve the existing architecture and public
tool envelope while making failure, qualification, and fallback behavior explicit.

## Non-negotiable boundaries

- Work only on `codex_changes`. Never switch, merge, rebase, commit, or push to `main`.
- Do not deploy or mutate Cloud Run, Vercel, provider accounts, registries, or production.
- Do not call live sports APIs or regenerate committed datasets from the network.
- Do not touch the pre-existing `.gitignore` edit or `review-phase1-cleanup.md`.
- Keep football → F1 → cricket ordering.
- Every tool continues to route through `FallbackChain` and return the standard envelope.
- Local development and tests remain healthy with diskcache and no Redis daemon.
- Implement one batch at a time, test-first, with a focused commit after verification.

## Selected approach

Use incremental, compatibility-preserving changes rather than a core rewrite. Security
controls live at the HTTP/tool boundaries, backend fixes retain current interfaces where
possible, and football output gains explicit fields while preserving `p_advance`.

Rejected alternatives:

- A documentation-only/minimal rename would leave the hosted endpoint and football model
  behavior incorrect.
- A generalized policy framework or full tool-validation abstraction would expand the
  blast radius without being required for the verified defects.

## Batch 1 — Repair and test the hooks

### Root cause

Both hook surfaces combine a Python heredoc with a here-string on `python3 -`. The
here-string replaces the interpreter program on stdin, parsing fails, and `|| true`
hides the error. A destructive command, a safe command, and malformed JSON therefore
all currently exit 0.

### Design

- Replace the conflicting stdin redirections with one JSON input path and a `python3 -c`
  parser.
- The destructive-command hook fails closed with exit 2 for malformed input, missing
  `tool_input.command`, and blocked commands.
- Normalize repeated whitespace and cover equivalent destructive forms such as flag
  reordering, absolute `rm` binaries, force pushes, and hard resets against remote refs.
- Keep the denylist deliberately small; it is a guardrail, not a shell parser.
- Repair the format hook's JSON extraction through the same single-input pattern. A
  malformed hook event exits non-zero so integration breakage is visible.
- Keep `.claude/hooks/` and `.codex/hooks/` byte-equivalent rather than adding a new
  helper abstraction.
- Replace absolute machine paths in `.codex/hooks.json` with repository-relative paths.

### Verification

Add `tests/hooks/test_agent_hooks.sh` covering both hook copies:

- known destructive variants exit 2;
- safe commands exit 0;
- malformed/missing-command JSON is rejected;
- a temporary badly formatted Python file is formatted by the post-write hook;
- non-Python paths are unchanged.

## Batch 2 — Correct README and SECURITY claims

### Design

- Replace “no data collection” with the actual telemetry inventory: client software
  name/version, User-Agent, tool name, outcome, latency, source, and staleness. Note that
  Cloud Run platform logs may include network/request metadata; local stdio logs stay on
  the operator's machine.
- Replace “host holds no secrets” with an honest capability statement: the public host may
  carry operator-owned provider credentials (the project journal records CricAPI), while
  local installs can run keyless or with BYO keys. Do not claim unverified live key state.
- Replace “all 44 tools work out of the box” with a three-context capability table:
  hosted endpoint, local keyless install, and local BYO-key install.
- Remove the false universal 200-item/500-character output-limit statement. In the Batch 2
  commit, state honestly that there is not yet an application-level MCP request ceiling.
  After Batch 3 lands, update the same section to the implemented 1 MiB MCP request limit,
  64 KiB telemetry capture, 10 MiB upstream response ceiling, and tool-specific output
  bounds. State that the upstream ceiling is post-buffer until a separate streaming change
  lands.
- Instruct vulnerability reporters not to open public issues for unpatched findings and
  use the existing security email for sensitive reports. Enabling GitHub private
  vulnerability reporting is external account state and remains out of scope.
- Preserve historical audit results but remove “ship-ready/clean” as a current
  certification.

## Batch 3 — Hosted abuse controls

### HTTP request limits

Add a pure-ASGI `RequestLimitMiddleware`; never use `BaseHTTPMiddleware`.

- Apply only to HTTP `POST` requests whose rewritten path ends in `/mcp`; stdio and SSE
  response streaming are unchanged.
- `LegacyKeyPathMiddleware` remains outermost so `/u/<key>/mcp` is rewritten before
  limiting and client logging.
- Reject declared or observed request bodies larger than 1 MiB with HTTP 413.
- Buffer at most 1 MiB + 1 byte before calling FastMCP, then replay the accepted ASGI body
  unchanged. This bounds memory while leaving response streaming untouched.
- Enforce a per-client fixed-window limit of 60 accepted POSTs/minute and a global limit
  of 300 accepted POSTs/minute per process. Return HTTP 429 plus `Retry-After` before MCP
  processing; rejected requests make no adapter/tool call.
- On Cloud Run (`K_SERVICE` present), use the validated leftmost IP in
  `X-Forwarded-For`; elsewhere ignore that header and use the ASGI peer address. Invalid
  or absent identities share an `unknown` bucket. Hash client identifiers in cache keys
  with `blake2s(digest_size=8)`.
- Expose the four defaults as positive settings with `SPORTIQ_` environment aliases:
  body bytes, client requests/minute, global requests/minute, and expensive-tool
  concurrency. No disable switch is added.

### Atomic counters

- Add dedicated counter operations to `Cache`; do not mix raw integer counters with the
  timestamp-wrapped JSON value format used by normal cached data.
- Redis uses one atomic increment/initial-expiry operation; diskcache uses a transaction
  around increment and initial expiry.
- Rewrite provider budget consumption to use the atomic counter path. `has_budget()`
  remains a peek, so the documented in-flight peek→fetch gap remains; lost increments do
  not.
- Request limiting increments before accepting work, so concurrent requests cannot all
  pass the same remaining-token read.

### Telemetry and expensive tools

- Cap `ClientInfoMiddleware` body capture at 64 KiB even though the accepted request may
  be larger. Forward/replay bytes unchanged and log no request body.
- Bound logged client name/version/User-Agent lengths and remove control characters.
- Replace the unused server semaphore with a concurrency limit of 2 around the explicitly
  expensive tools: football group/bracket/knockout simulations, F1 pit strategy, and the
  Dream11 solver. Reuse the existing registry wrapping point so the 44 tool bodies stay
  untouched.
- The semaphore bounds overlap but does not claim to offload synchronous CPU work; worker
  offloading remains a separate measured optimization.

### Deployment boundary

Update `cloud.md` to record that per-process diskcache/counters require one maximum Cloud
Run instance. Do not run `gcloud`, deploy, or change the live instance setting.

## Batch 4 — Scoped backend contract fixes

### Expected failures

- At every football/F1 raw and intel chain boundary that can surface it, catch
  `NotFoundError` alongside `AllSourcesFailedError` and return `NOT_FOUND`, preserving
  attempts/suggestions where available.
- Do not catch arbitrary exceptions or collapse them into `NOT_FOUND`.

### HTTP redirects

- Resolve a relative `Location` with `urljoin(response.request.url, location)` before
  normalized scheme/host/port comparison.
- Continue blocking cross-host, scheme-changing, and port-changing redirects and keep the
  five-hop ceiling.

### Cache lifecycle and corrupt entries

- Add explicit close and single-key delete operations for diskcache and Redis.
- Treat malformed cached records as a miss: log a scrubbed warning, evict only that key,
  and let the chain fetch normally.
- Close isolated test caches so `pytest -W error::ResourceWarning` is clean.
- Integrate best-effort server shutdown without making Redis or an event loop a local
  requirement.

### Health identity

- Deduplicate adapters using an optional `health_name`, defaulting to `name`.
- Give football and cricket static datasets distinct health names while preserving their
  response `source` values.
- Give both Odds API adapters the same health identity and keep shared quota aggregation
  by `budget.source`.

### Verified input bounds

Keep validation next to each tool and return `INVALID_INPUT` envelopes. Cover only the
verified gaps:

- football: trimmed nonempty team/group values, different matchup participants after
  normalization, group A–L, nonnegative NumPy seeds, and existing 100-character limits;
- F1: driver numbers 1–99, positive session keys, laps 1–200, and
  `current_lap <= total_laps`;
- cricket H2H/player-matchup paths: trimmed nonempty identifiers, 200-character ceiling,
  and different participants after `casefold()`.

Do not introduce a shared validation framework.

## Batch 5 — Football correctness

### Correct group qualification probabilities

- Add a full 12-group qualification-stage Monte Carlo using the same group simulation and
  best-third selection as the bracket engine.
- `football_simulate_group` still returns the requested group only, but each iteration
  evaluates all groups so third-place qualification is contextual.
- Return per team:
  `p_first`, `p_second`, `p_third`, `p_fourth`, `p_auto_advance`,
  `p_best_third_advance`, `p_advance`, and `avg_points`.
- Preserve `p_advance` for clients but redefine it as true Round-of-32 probability:
  `p_auto_advance + p_best_third_advance`.
- Preserve the invariants: auto-advance mass per group is 2; Round-of-32 mass across all
  groups is 32; probabilities remain reproducible at the pure-model layer.

### Stage-aware results and penalty winners

- Normalize provider match ID, stage/round, and winner signal in every football fixtures
  adapter without changing chain order.
- Prefer explicit stage information when classifying a finished fixture. Fall back to
  group membership only for legacy/static payloads with no stage.
- Key provider reports by normalized match ID where available, otherwise by stage class
  plus pairing, so a same-group knockout rematch cannot replace the group result.
- Preserve both matches in chronological Elo input.
- When a knockout score is level and the provider supplies a penalty winner, lock that
  winner. Continue dropping an undecidable level knockout result.

### FIFA 2026 tiebreak policy

Use the official published order where current inputs support it:

1. head-to-head points among the tied teams;
2. head-to-head goal difference;
3. goals scored in all group matches;
4. overall goal difference;
5. overall goals scored;
6. team conduct score;
7. latest FIFA men's ranking.

The runtime has no conduct feed or committed FIFA-ranking snapshot. When a tie survives
the available criteria, use the existing model rating as an explicit deterministic proxy,
then RNG only for equal model ratings. Count and expose these fallbacks in simulation
metadata; never label the fallback as official FIFA data.

Use the same points/GD/GF then model-rating fallback for ranking third-placed teams when
conduct/ranking data is unavailable.

Source: FIFA, “World Cup 2026 groups: How teams qualify and tie-breakers,” published
2026-06-13: <https://www.fifa.com/en/articles/groups-how-teams-qualify-tie-breakers>.

## Tests and verification

Every behavior change follows red→green TDD. Focused tests run after each change; each
batch then runs its affected suite. Final offline gate:

```bash
bash tests/hooks/test_agent_hooks.sh
uv lock --check
uv run ruff check .
uv run pytest -W error::ResourceWarning
uv run bandit -r src -ll --quiet
uv run python scripts/check_release_build.py
```

No live API test, Inspector network install, cloud smoke, deployment, publish, or website
production check is part of this branch task.

## Branch-local memory and documentation

Tracked memory updated as the relevant batch lands:

- `GAPS.md`: status each resolved/partially resolved finding and retain remaining caveats.
- `PROJECT.md`: request-limit flow, atomic counter/lifecycle behavior, health identity, and
  football qualification/result/tiebreak behavior.
- `docs/hot.md`: replace the stale 35-tool/step8 state with the current branch focus.
- `docs/wiki/decisions/0012-hosted-abuse-controls.md`: durable thresholds, identity,
  single-instance assumption, and trade-offs; add to `docs/index.md`.
- Relevant tool/model/data-source wiki pages for request behavior and football semantics.
- Both `.agents/skills/monte-carlo-bracket/SKILL.md` and
  `.claude/skills/monte-carlo-bracket/SKILL.md`, removing the stale claim that official
  Annex C allocation is absent.
- `docs/log.md`: append local entries after meaningful operations even though the journal
  is intentionally gitignored.

The ignored `codex_changes*.md` planning artifacts and external Codex `MEMORY.md` files are
not branch memory and will not be edited.

## Out of scope

- Any change to `main`, branch integration, push, PR, publish, release, or deployment.
- Live Cloud Run verification or configuration changes, including `max-instances`.
- Streaming the upstream 10 MiB HTTP response limit.
- Provider charge-on-attempt research or policy changes.
- Redis re-probing after downgrade or adopting hosted Redis.
- F1 optimizer/model redesign, Dream11 player projections, new tools, or new sports.
- Adding fair-play/FIFA-ranking datasets without a regenerable approved source pipeline.
- Broad response-output truncation or a new validation abstraction.
