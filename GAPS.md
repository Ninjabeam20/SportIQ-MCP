# GAPS.md — Honest audit of weaknesses

> Written 2026-07-07 against v0.3.1 (commit `b7a1392`). Ordered by severity, most important
> first. Each entry: what it is, where it lives, why it matters, and a fix scoped small enough
> to execute as a single task. Severity: **HIGH / MEDIUM / LOW**.
>
> Context that shapes severity: the hosted instance is a free public Cloud Run service running
> diskcache (no Redis), stdio installs are single-user, and the project has a hard zero-spend
> constraint. Several "known limitations" below are documented in code comments — they are
> listed anyway because a future contributor must know which ones are load-bearing accepted
> trade-offs vs. genuine debt.

---

## 1. HIGH — No per-client rate limiting on the hosted endpoint; shared upstream quotas are a public DoS surface

- **What:** The Cloud Run deployment serves `/mcp` with no authentication and no per-client
  throttling. Server-side keys are configured on the host (CRICAPI_KEY was added 2026-07-03;
  CricAPI = 100 req/day hard cap, The Odds API = ~16/day slice). Per-source budgets
  (`core/ratelimit.py`) protect the *upstream* from the *server*, but nothing protects the
  server's quota pool from a single abusive or merely enthusiastic client. One user scripting
  `cricket_get_live_matches` in a loop exhausts CricAPI for every hosted user until midnight
  reset; the chain then degrades to scrapers-off → stale → `ALL_SOURCES_FAILED`.
- **Where:** `src/sportiq/server.py` (HTTP branch of `main()`), absence of any middleware in
  `src/sportiq/core/` doing per-client accounting. `ClientInfoMiddleware`
  (`src/sportiq/core/client_info.py`) already extracts client identity but only logs it.
- **Why it matters:** availability of the flagship live tools for all hosted users hinges on the
  politeness of each individual anonymous client. This is the highest-leverage gap because the
  caching layer makes it invisible until the day it isn't.
- **Suggested fix (single task):** add a pure-ASGI (NOT BaseHTTPMiddleware — see PROJECT.md §6.2)
  middleware that keys a token bucket on client IP (`X-Forwarded-For` head, Cloud Run sets it)
  using the existing cache-backed counters in `core/ratelimit.py` (e.g. 60 req/min per IP), and
  returns 429 with `Retry-After` beyond it. Wire it in `server.py` next to the other two
  middlewares, HTTP transport only. Unit-test like `tests/unit/test_path_compat_middleware.py`.

## 2. HIGH — Rate-limit counters are non-atomic (read-modify-write) and the peek→consume gap allows double-spend

- **What:** `has_budget()` and `consume()` in `src/sportiq/core/ratelimit.py` do
  `get → compare/add → set`. Two concurrent requests both peek "1 token left", both fetch, both
  consume — counter says 1 spent, upstream saw 2 calls. `consume()` itself is also
  get-then-set, so concurrent increments can lose updates (undercounting = quota overspend).
  The docstring acknowledges this "as a documented local-dev limitation" — but the hosted HTTP
  deployment is concurrent by nature, so the limitation applies exactly where budgets matter most.
- **Where:** `src/sportiq/core/ratelimit.py:18-63`; consumers in
  `src/sportiq/core/fallback.py:124-143,190-191`.
- **Why it matters:** the entire quota-protection design ("burning quota = whole tool dies for
  everyone", `.claude/rules/api-budgets.md`) rests on these counters. Overspend on CricAPI's
  100/day or The Odds API's 16/day slice defeats the design silently.
- **Suggested fix (single task):** add an atomic `incr(key, ttl)` to `Cache`
  (`src/sportiq/core/cache.py`) — `INCR`+`EXPIRE` on the Redis path, `diskcache.Cache.incr()`
  (which is transactional) on the disk path — and rewrite `consume()` to use it. That fixes lost
  increments outright. The peek→consume race window remains but shrinks to over-by-in-flight-count;
  note it in the docstring. Extend `tests/unit/` with a concurrent-consume test using
  `asyncio.gather`.

## 3. MEDIUM — `NotFoundError` from chains is uncaught in football and F1 raw/intel tools (latent envelope-contract crash)

- **What:** `FallbackChain.fetch()` can raise `NotFoundError` (fallback.py:221). Cricket tools
  catch it everywhere (regression-locked per the NOT_FOUND-invariant finding), but
  `src/sportiq/football/tools.py` catches only `AllSourcesFailedError` (all 7 tools), as do
  `src/sportiq/f1/tools.py` (all 6) and most of `src/sportiq/football/intel_tools.py`.
  Today this is *latent*, not live: football chains that contain a NotFound-raising adapter
  (api_football fixtures/squad) also contain a non-NotFound-failing or terminating adapter, so
  the "every adapter raised NotFoundError" condition can't currently be met; F1 adapters never
  raise it. But the invariant is one adapter-edit away from breaking: e.g. giving
  `FootballDataOrgTeamStatsAdapter` an empty-payload NotFound guard (mirroring the api_football
  fix from 2026-07-03 — a *recommended* pattern per that incident) would make
  `football_get_match_stats` crash with a raw exception instead of a `NOT_FOUND` envelope.
- **Where:** `src/sportiq/football/tools.py` (every `except AllSourcesFailedError`),
  `src/sportiq/f1/tools.py` (same), `src/sportiq/football/intel_tools.py` (lines 125, 171, 218,
  262, 292, 425).
- **Why it matters:** "Every tool returns either `{data, meta}` or `{error}` — never neither"
  is the core contract (`.claude/rules/error-envelope.md`). An uncaught exception surfaces as a
  generic FastMCP error, breaking clients that branch on the envelope, and the failure mode only
  appears when a specific entity is missing — i.e. rarely and in production.
- **Suggested fix (single task):** in the three files, widen each handler to
  `except (AllSourcesFailedError, NotFoundError) as e:` and emit `code="NOT_FOUND"` when
  `isinstance(e, NotFoundError)` (cricket tools show the exact pattern to copy —
  `src/sportiq/cricket/tools.py:71,101`). Add one regression test per sport in `tests/tools/`
  with a stub chain raising `NotFoundError`.

## 4. MEDIUM — Redirect handling in the shared HTTP client breaks on relative `Location` headers

- **What:** `_fetch_json_once()` (`src/sportiq/core/http.py:72-103`) follows redirects manually.
  A relative `Location` (e.g. `/v4/competitions/WC`) has an empty `netloc`, passes the same-host
  check, and is then passed to `client.get(location)` — but the shared client has no `base_url`,
  so httpx raises `InvalidURL`/`UnsupportedProtocol` instead of following. Relative Locations are
  legal (RFC 7231 §7.1.2) and common.
- **Where:** `src/sportiq/core/http.py:82-97`.
- **Why it matters:** any upstream that starts answering with a relative-redirect (CDN or API
  version migration — exactly the situation redirects exist for) makes that adapter hard-fail
  with a confusing transport error rather than following one hop. Given fallback chains, the
  symptom would be a silent shift to a lower-priority source — hard to notice, quota-relevant.
- **Suggested fix (single task):** resolve `location` against `str(response.request.url)` with
  `urllib.parse.urljoin` before the host check and the follow-up GET. Add a respx test with a
  relative-Location 302 in `tests/unit/test_s6_http_hardening.py`.

## 5. MEDIUM — Stampede guard and cache/rate-limit state are per-process; multi-instance Cloud Run multiplies quota burn

- **What:** three pieces of state assume one process: `FallbackChain._key_locks`
  (`src/sportiq/core/fallback.py:74,101-113`) serializes concurrent misses per key;
  the diskcache backend (`src/sportiq/core/cache.py`) is a per-container filesystem; and the
  rate-limit counters live in that cache. Cloud Run can scale to N instances (and replaces
  instances on deploy), so each instance keeps its own cache, its own counters, and its own
  stampede locks. Effective upstream spend = configured budget × live instances, and cold
  instances re-fetch everything.
- **Where:** `src/sportiq/core/fallback.py`, `src/sportiq/core/cache.py`,
  `src/sportiq/core/ratelimit.py`; deployment config in `cloudbuild.yaml` / Cloud Run service.
- **Why it matters:** currently mitigated by low traffic and (likely) max-instances=1-ish
  scaling, but nothing in the repo pins that; a traffic spike that fans out to 3 instances
  triples CricAPI spend invisibly.
- **Suggested fix (single task):** this is an accepted zero-spend trade-off (Redis costs money),
  so the *executable* fix is a guardrail, not a rewrite: set/verify `--max-instances=1` on the
  Cloud Run service and record the invariant in `cloud.md` + a comment atop `ratelimit.py`
  ("budget math assumes a single instance"). Revisit Redis (Upstash free tier) only when traffic
  justifies it.

## 6. MEDIUM — sdist safety is a hand-maintained blocklist; every new root doc is a potential leak into PyPI

- **What:** hatchling's sdist includes the whole tree minus `[tool.hatch.build.targets.sdist]
  exclude` (`pyproject.toml:68-93`), and the CI gate (`scripts/check_release_build.py`) checks a
  parallel, *manually duplicated* substring blocklist. The repo root accumulates business-private
  docs constantly (`sponsor-ledger.md`, `monetization-*.md`, `free-rollback-plan.md`,
  `v2a-testing-checklist.md`, `launch.md`, …); each new one must be remembered in up to three
  places (.gitignore, pyproject exclude, check script). `BACKERS.md`, `cloud.md`, `dev.md`,
  `LEARNING-GUIDE.md`, `dashboard.html`, `glama.json`, `datasets/`, `done/` are examples of files
  currently shipping (or shippable) in the sdist that no PyPI consumer needs. This very audit
  (`GAPS.md`) would ship too.
- **Where:** `pyproject.toml` (sdist excludes), `scripts/check_release_build.py`
  (SENSITIVE_PATTERNS).
- **Why it matters:** the failure mode is silent one-way disclosure — a forgotten
  `sponsor-notes.md` lands on PyPI forever. Two blocklists that must be kept in sync is exactly
  the kind of thing that drifts.
- **Suggested fix (single task):** flip the sdist definition to an **allowlist**:
  `[tool.hatch.build.targets.sdist] include = ["src/", "README.md", "LICENSE", "pyproject.toml", "SECURITY.md"]`
  (plus whatever the registry marker needs). Keep `check_release_build.py` as the independent
  verifier, but change its logic to "fail on any member NOT under the allowlist" so new files are
  excluded-by-default. Verify with `uv run python scripts/check_release_build.py`.

## 7. LOW — Dead code: `_SERVER_SEMAPHORE` is created and never used

- **What:** `src/sportiq/server.py:28` creates `asyncio.Semaphore(20)` with a comment
  "not wired into tools yet; available when fan-out is added." Nothing imports or acquires it.
  It also creates the semaphore at import time, outside any running event loop.
- **Where:** `src/sportiq/server.py:27-28`.
- **Why it matters:** it advertises a concurrency cap that does not exist — a reader (or a
  smaller model) will assume the server is bounded at 20 concurrent calls. Half-built
  affordances are worse than absent ones.
- **Suggested fix (single task):** delete the two lines (it is recoverable from git history), or
  wire it into `core/tool_telemetry.instrument_tools()`'s wrapper (`async with _SERVER_SEMAPHORE:`)
  if the cap is actually wanted. Deleting is the simpler, rule-compliant option.

## 8. LOW — Envelope is an untyped open `TypedDict`, contradicting the project's own FastMCP convention

- **What:** `.claude/rules/fastmcp-conventions.md` says "Pydantic models preferred for structured
  returns" and bans untyped dicts, but every tool returns `Envelope`
  (`src/sportiq/core/tool_response.py:6-26`) whose `data`/`meta`/`error` are open
  `dict[str, Any] | None`. The docstring explains why (per-tool fields pass through
  unconstrained, and FastMCP null-fills absent keys), so this is a *deliberate* deviation — but
  the rule file doesn't record the exception, so the codebase disagrees with itself on paper.
- **Where:** `src/sportiq/core/tool_response.py`, `.claude/rules/fastmcp-conventions.md`.
- **Why it matters:** a future contributor following the rules verbatim will "fix" tools toward
  per-tool Pydantic returns, breaking envelope uniformity and the outputSchema-null dance the
  TypedDict comment documents.
- **Suggested fix (single task):** add two sentences to `fastmcp-conventions.md`: return type is
  always `Envelope` (the sanctioned exception to "Pydantic preferred"), and why. No code change.

## 9. LOW — Stale docstring in `tests/conftest.py` claims healthchecks make live HTTP calls

- **What:** `no_live_credentials`' docstring (`tests/conftest.py:29-36`) justifies itself with
  "Some healthchecks (e.g. CricAPILiveMatchesAdapter) make a live HTTP call when their key is
  truthy". That was true once; healthchecks are now key-presence-only precisely to avoid quota
  burn (`src/sportiq/cricket/adapters/cricapi.py:54-58`). The fixture is still essential (adapter
  `fetch()` paths would hit live APIs), but its stated rationale is wrong.
- **Where:** `tests/conftest.py:27-46`.
- **Why it matters:** misleading rationale invites someone to "simplify" the fixture away after
  checking healthchecks and finding them harmless, silently re-enabling live HTTP in tests when a
  `.env` key is present — violating the hardest testing rule in the repo.
- **Suggested fix (single task):** rewrite the docstring: the guard exists because `settings`
  loads the developer's `.env` and any test that exercises a real adapter `fetch()` (or forgets a
  respx mock) would otherwise hit live upstreams and burn quota. One-file comment edit.

## 10. LOW — Redis downgrade is permanent per process, with no re-probe

- **What:** on the first Redis error, `Cache._downgrade_to_disk()`
  (`src/sportiq/core/cache.py:72-79`) switches the backend to diskcache for the life of the
  process — a Redis blip (restart, failover) permanently silences it until the server restarts.
  Deliberate ("never crash tools over cache"), but there is no path back and no health surfacing
  beyond `cache_backend` in `sportiq_health`.
- **Where:** `src/sportiq/core/cache.py:72-79`.
- **Why it matters:** low today (no environment actually runs Redis), but if Redis is ever
  introduced for gap #5, a 1-second network blip degrades the shared cache/counters to
  per-instance and re-opens the quota multiplication problem invisibly.
- **Suggested fix (single task):** record a `downgraded_at` timestamp; in `get`/`set`, re-attempt
  `_init_backend()` at most once every N minutes (e.g. 5). Keep the fail-open semantics. Add a
  unit test alongside `tests/unit/test_cache.py`. Defer until Redis is actually deployed.

## 11. LOW — `football_get_odds` team filter rebuilds the payload and drops any sibling keys

- **What:** `src/sportiq/football/tools.py:201-202` replaces the whole value with
  `{"events": [...]}` when a team filter is applied. Today the odds payload only has `events`,
  so nothing is lost — but if the adapter ever adds a sibling key (e.g. `fetched_at`,
  `bookmaker_count`), the filtered path silently drops it while the unfiltered path keeps it,
  and the divergence won't be caught by shape tests that only assert `events`.
- **Where:** `src/sportiq/football/tools.py:200-203`.
- **Suggested fix (single task):** mutate in place instead:
  `result.value["events"] = _filter_events_by_team(result.value["events"], team)`.
  One-line change; existing tests in `tests/tools/test_odds_tools.py` still pass.

## 12. LOW — Version must be bumped by hand in `server.json` (process gap, already bit once)

- **What:** the MCP registry manifest `server.json` carries its own version string, disconnected
  from `pyproject.toml`. It has already drifted two minors behind once (0.2.1 vs 0.3.0) before
  being caught. `__init__.__version__` was fixed to read package metadata dynamically; the
  manifest was not, because the registry requires a literal.
- **Where:** `server.json`; release flow documented in the publish-pipeline memory and
  `.github/workflows/release.yml` (which does not touch server.json).
- **Suggested fix (single task):** add a check to `scripts/check_release_build.py` (which already
  runs in CI and in the release workflow) asserting `server.json`'s version equals
  `pyproject.toml`'s — fail the build on drift instead of relying on memory.

## 13. LOW — Coverage blind spots: `server.py` transport wiring and all of `scripts/` are untested

- **What:** `src/sportiq/server.py` is excluded from coverage (`pyproject.toml:113-117`) and has
  no direct tests — the stdio/HTTP branch of `main()`, middleware ordering (LegacyKeyPath must be
  outermost), and the "don't use `mcp.run('streamable-http')` or middlewares drop" invariant are
  enforced only by comments. The middlewares themselves ARE unit-tested
  (`test_path_compat_middleware.py`, `test_client_info_middleware.py`), and prod deploys go
  through a manual canary smoke test — so the risk is a wiring regression, not component bugs.
  Separately, `scripts/build_wc2026_*.py` regenerate committed data files with only downstream
  validation (`test_bracket_data.py` checks invariants of the artifact, not the generator).
- **Where:** `src/sportiq/server.py`, `pyproject.toml` coverage omit list, `scripts/`.
- **Suggested fix (single task):** add one unit test that imports `sportiq.server`, monkeypatches
  `uvicorn.run` to capture the app, sets `SPORTIQ_TRANSPORT=http`, calls `main()`, and asserts
  middleware order (`LegacyKeyPathMiddleware` before `ClientInfoMiddleware`) and port/host
  settings. Keep server.py in the coverage omit list (the stdio branch blocks forever by design).

## 14. INFO — Accepted risks worth restating so nobody "fixes" them

Not debt, but each looks like a bug to fresh eyes:
- **diskcache pickle CVE (CVE-2025-69872) is deliberately ignored** in pip-audit
  (`.github/workflows/security.yml`) — the cache is local-only, values are self-produced JSON.
- **DNS-rebinding protection disabled** on HTTP transport (`server.py:72-74`) — required for
  Cloud Run host headers; perimeter security is Cloud Run's.
- **`time_budget_s=12` cannot preempt sync-blocking adapters** (fastf1) — documented in
  `fallback.py:66-70`.
- **Scrapers ship disabled** (ADR-0007) and must stay opt-in via env flags.
- **Elo seed is frozen** (D1 finding) — do not re-tune it; use `SPORTIQ_FOOTBALL_LIVE_ELO` walk.
- **Local dev/prod host run diskcache, not Redis** — a healthy state, not degradation.
