# PROJECT.md — SportIQ MCP: The Full Picture

> Deep knowledge-transfer document, written 2026-07-07 against v0.3.1 (commit `b7a1392`) and
> refreshed 2026-07-14 on `codex_changes` after the hardening/correctness batches.
> Read this first. For known weaknesses read `GAPS.md`. For operational rules read `CLAUDE.md`.

---

## 1. What this is

**sportiq-mcp** is a Python MCP (Model Context Protocol) server that turns any AI assistant
(Claude, ChatGPT, Cursor, …) into a sports analyst across three sports: **FIFA World Cup 2026
football, Formula 1, and IPL cricket**. It exposes **44 AI-callable tools** — plus one meta-tool
(`sportiq_health`) — over stdio (local install via `uvx sportiq-mcp`) or streamable-HTTP (hosted
on Google Cloud Run at `sportiq-mcp-329580761892.us-central1.run.app/mcp`).

**Who it's for:** end users are AI-assistant users who want live sports data and — the actual
product — the *intelligence layer*. Raw data tools (fixtures, standings, lap times, scorecards)
are table stakes. Three flagship tools are the differentiator:

| Flagship | What it does | Engine |
|---|---|---|
| `football_simulate_bracket` | Monte Carlo the full 48-team WC 2026 into per-team round + title probabilities | Poisson xG driven by Elo ratings, conditioned on real completed results |
| `f1_predict_pit_strategy` | Optimal pit-stop laps + compound sequence | Linear tyre-degradation fits on OpenF1 telemetry + measured per-circuit pit loss |
| `cricket_build_dream11_team` | Valid fantasy XI + captain/vice-captain under credit/role/team caps | PuLP ILP solved with CBC |

**Business context:** everything is free (the paywall was removed in v0.3.0; the paid edition is
preserved at git tag `v0.2.3` / Cloud Run rev `00023-kay`). Monetization is GitHub Sponsors
donations. The project doubles as the author's portfolio piece. Hard constraint: **zero
infrastructure spend until traffic justifies it** — BYO API keys, no Redis in prod, no
min-instances, free tiers everywhere.

**Ordering convention that permeates everything:** football → F1 → cricket. Headings, lists,
tables, tool registration order — always that order.

---

## 2. Tech stack and why

| Piece | Choice | Why (from ADRs in `docs/wiki/decisions/` and code comments) |
|---|---|---|
| Runtime | Python 3.11+ | scipy/numpy/pandas ecosystem; MCP SDK is Python-first |
| MCP framework | `mcp` SDK, FastMCP decorator API | ADR-0001: docstrings + type hints *are* the tool schema; far less boilerplate than raw MCP |
| Packaging | `uv` + `pyproject.toml`, shipped via `uvx` | ADR-0004: zero-install UX for end users (`uvx sportiq-mcp` in any MCP client config) |
| HTTP | `httpx` (async) + `tenacity` | Single shared client (`core/http.py`) as choke point for timeouts, retry, redirect and size hardening |
| Schemas | pydantic v2 + pydantic-settings | Config from `.env`; error models validated |
| Cache | Redis primary, `diskcache` automatic fallback | ADR-0003: local dev must never require a daemon; prod host actually runs diskcache too (zero-spend rule) |
| ILP solver | PuLP + CBC binary | ADR-0002: OR-Tools deliberately excluded (heavy dependency); CBC is apt/brew-installable |
| Stats | scipy (Poisson) + numpy (vectorized Monte Carlo) | Bracket sim runs thousands of iterations per call |
| DataFrames | pandas | F1 lap-time regression fits |
| F1 telemetry | `fastf1` — **optional extra**, lazy-imported | Huge dependency; only needed for one local adapter |
| Testing | pytest + pytest-asyncio (auto mode) + respx | ADR-0006: no live HTTP in tests, ever; cassettes in `tests/fixtures/` |
| Lint | ruff (line 100, E/F/I/W/UP/B/SIM/RUF) | |
| Logging | structlog — JSON on Cloud Run (auto-detected via `K_SERVICE`), pretty locally | Cloud Logging parses JSON into `jsonPayload` for the analytics dashboard |
| Deploy | Docker → Cloud Run, Kaniko cached builds (`cloudbuild.yaml`) | Stub-package trick in Dockerfile keeps the heavy scipy/pandas layer cached across source edits |
| Publish | GitHub Actions OIDC Trusted Publishing to PyPI on `v*` tags | ADR-0010: no long-lived PyPI token in secrets |

**Deliberately excluded** (do not add): OR-Tools, SQLAlchemy, FastAPI, OpenTelemetry, any
database other than Redis/diskcache.

---

## 3. Architecture

### 3.1 The one diagram that matters

```
MCP client (Claude / Cursor / ChatGPT)
        │  stdio (uvx)  or  streamable-HTTP (/mcp on Cloud Run)
        ▼
src/sportiq/server.py ── FastMCP("sportiq")
        │   registration order = relevance: health → instructions → prompts
        │   → football → F1 → cricket → cross-sport
        │   then: apply_param_descriptions()  (docstring Args → tool schema)
        │   then: instrument_tools()          (per-call telemetry wrapper)
        ▼
TOOLS  (src/sportiq/{sport}/tools.py = RAW, intel_tools.py = INTEL)
        │   thin: validate args → chain.fetch() → {data, meta} envelope
        │   INTEL tools additionally call MODELS (pure functions, no I/O)
        ▼
FallbackChain singletons  (src/sportiq/{sport}/chains.py — module level)
        │   1. fresh cache hit? return
        │   2. per-key asyncio.Lock (stampede guard), re-check cache
        │   3. walk adapters in order: budget peek → fetch (12s wall cap)
        │      → success: consume budget token, cache write, return
        │   4. all failed: stale cache within stale_ttl? return is_stale=True
        │   5. else raise NotFoundError (all raised NF) / AllSourcesFailedError
        ▼
ADAPTERS (src/sportiq/{sport}/adapters/*.py)
        │   one class per (source, data-shape); all use core/http.get_json()
        ▼
core/cache.py (Redis→diskcache)   core/ratelimit.py (token buckets in cache)
core/http.py (shared httpx client: retry, same-host redirects, 10MB cap)
```

### 3.2 The layers, concretely

- **`src/sportiq/server.py`** — entry point. `main()` is the uvx contract
  (`[project.scripts] sportiq-mcp = "sportiq.server:main"`). Default transport is stdio;
  `SPORTIQ_TRANSPORT=http` builds the Starlette app manually (NOT via `mcp.run("streamable-http")`,
  which would drop the middlewares) and runs uvicorn with three **pure-ASGI** middlewares:
  `RequestLimitMiddleware` (1 MiB + per-client/process admission), `ClientInfoMiddleware`
  (bounded/sanitized client logging), and `LegacyKeyPathMiddleware` (rewrites the paid-era
  `/u/<key>/mcp` sponsor-connector paths to `/mcp`).

- **`src/sportiq/core/`** — everything sport-agnostic:
  - `fallback.py` — **the** load-bearing file. `FallbackChain[T]`, `Adapter` protocol,
    `FallbackResult`. Read it in full before touching anything data-flow-related.
  - `tool_response.py` — `Envelope` TypedDict (declared return type of every tool → FastMCP emits
    `outputSchema`), `tool_response()`, `error_envelope()`, `paginate()`, `truncate_payload()`,
    `staleness_meta()` (worst-case staleness aggregation for multi-chain INTEL tools).
  - `errors.py` — `SportiqError` hierarchy + `ErrorCode` literal. Note `MissingCredentialsError`
    maps to code `ALL_SOURCES_FAILED` on purpose — the chain walks past keyless adapters as a
    normal failure.
  - `cache.py` — unified wrapped-value cache plus atomic raw counters, delete/close lifecycle,
    and corrupt-entry eviction. Redis errors downgrade *permanently for the process* to diskcache.
  - `ratelimit.py` — `Budget(source, per_minute, per_day)`, `has_budget()` (peek), atomic
    `consume()` (after success only), `remaining()` (for health). The peek→fetch race remains.
  - `http.py` — `get_json()` (retries transport + 5xx only, never 429) and `get_json_burst()`
    (also retries 429 — ONLY for no-quota sources like OpenF1). Relative redirects are resolved
    before full-origin checks; upstream responses have a post-buffer 10 MiB cap.
  - `redact.py` — `scrub()` strips API keys from exception strings before they land in attempt
    logs / error envelopes (keys travel as URL query params for some sources; ADR-0009).
  - `health.py` — `sportiq_health` tool; adapters self-register (deduped by optional
    `health_name`, otherwise name); healthchecks are key-presence-only.
  - `param_docs.py` — post-registration shim that parses docstring `Args:` blocks into the tool
    JSON schema (FastMCP only schemas type hints; directories like Smithery score param docs).
  - `tool_telemetry.py` — wraps every registered tool to emit a structlog `tool_call` event
    (success, latency, error code, client) and shares a concurrency-two semaphore across the
    five expensive football/F1/cricket paths.
  - `prompts.py`, `instructions.py` — MCP prompts + an instructions resource.
  - `parlay.py`, `value_bet.py` — shared math for accumulator/value-bet tools across sports.

- **`src/sportiq/{football,f1,cricket}/`** — identical internal shape per sport:
  - `adapters/` — one module per upstream; classes per data shape (e.g.
    `APIFootballFixturesAdapter`, `APIFootballSquadAdapter`). Constructors NEVER raise on missing
    credentials (so they still appear in health); `fetch()` raises `MissingCredentialsError` instead.
  - `chains.py` — module-level chain singletons wiring adapters in fallback order, with cache
    keys and TTLs per `.claude/rules/caching-policy.md`.
  - `tools.py` — RAW tools. `intel_tools.py` — INTEL tools (compose chains + models).
  - `models/` — pure computation, no I/O. This is where the flagship value lives.
  - `data/` — committed JSON seeds: `wc2026.json` (draw regenerated from football-data.org,
    2026-07-03), `wc2026_bracket.json` (official FIFA R32 template + 495-row Annex C best-thirds
    allocation), `elo_seed.json`, `football_squads.json`, `circuits.json` (measured pit-loss per
    circuit), `squads.json`, `venues.json` (cricket priors, 178 par).

- **`src/sportiq/server_tools/cross_sport.py`** — the one cross-sport tool
  (`cross_sport_build_accumulator`).

### 3.3 Data-source fallback orders (the operational heart)

- **Football fixtures:** api_football → football-data.org → openfootball (keyless GitHub JSON) →
  static seed. Standings: api_football → football-data.org → *derived* (computed keylessly from
  fixtures + results). Groups: static seed only (effectively infinite TTL). Odds: The Odds API only.
- **F1:** OpenF1 (live telemetry, keyless) and Jolpica (Ergast successor, keyless); optional
  local fastf1. No quotas, but cached aggressively for latency.
- **Cricket:** CricAPI (100 req/day!) → RapidAPI Cricbuzz (paid escape hatch) → opt-in scrapers
  (NDTV `SPORTIQ_ENABLE_NDTV=1`, Cricbuzz `SPORTIQ_ENABLE_CRICBUZZ=1`; disabled by default for
  ToS reasons, ADR-0007) → static seed terminators.
- **The Odds API** budget is shared cricket+football: one `theodds` source, `per_day=16`
  ≈ 480/month under the 500/month cap (there is no per-month unit in `Budget`).

Key principle: chains that must never fail end in a **static-seed terminator** (groups, squads
"empty-but-valid", venues). Chains without terminators (team_stats, odds) return clean
`ALL_SOURCES_FAILED` envelopes when keyless — that's by design, not a bug.

### 3.4 The models (where the flagships live)

- **Football** (`football/models/`): `elo.py` (frozen seed ratings — see D1 note below),
  `elo_live.py` (opt-in `SPORTIQ_FOOTBALL_LIVE_ELO`: walks Elo forward from completed WC matches),
  `poisson_xg.py` (Elo → per-team goal lambdas → scipy Poisson score matrix),
  `group_sim.py`, `bracket_sim.py` (one contextual 12-group draw per iteration: top two plus the
  eight best thirds → official 495-row Annex-C allocation → knockout tree → champion),
  `results_state.py` (stage-aware match IDs/winners preserve group/knockout rematches and lock
  real results), `form_trends.py`, `value_bet.py` (de-vig + model-edge).
- **F1** (`f1/models/`): `tyre_deg.py` (linear per-compound fits on lap times), `pit_strategy.py`
  (degradation + measured per-circuit pit loss from `circuits.json` → optimal stops),
  `undercut.py`, `race_pace.py`, `quali_analysis.py`.
- **Cricket** (`cricket/models/`): `dream11_solver.py` (PuLP ILP; needs a `cbc` binary on PATH),
  `captain_score.py`, `form_index.py`, `pitch_report.py` (venue priors), `player_matchup.py`,
  `head_to_head.py`, `win_probability.py` (gated/deferred — do not build inline; needs its own
  reliability-curve validation phase).

The skills `monte-carlo-bracket`, `f1-tyre-model`, and `dream11-scoring` document the domain math;
the wiki pages under `docs/wiki/models/` are the canonical derivations.

### 3.5 The knowledge system (docs/)

Karpathy three-layer ownership:
- `docs/raw/` — **immutable** user-dropped sources. Never modify.
- `docs/wiki/` — **LLM-owned** pages (tools/, chains/, models/, data-sources/, decisions/,
  findings/), all with YAML frontmatter, indexed one-line-each in `docs/index.md`. **Always read
  `docs/index.md` first for domain questions**; open only the 1–2 pages it points to.
- `CLAUDE.md` + `.claude/` — co-evolved rules.
- `docs/log.md` — append-only operations journal (`## [YYYY-MM-DD] op | subject`). This is the
  project's actual history; read the tail to know what happened recently.

### 3.6 Testing architecture

758 collected tests, four layers (see `.claude/rules/testing.md`):
`tests/unit/` (pure models + core, no I/O) → `tests/adapters/` (respx-mocked HTTP against
committed cassettes in `tests/fixtures/{source}/`) → `tests/chains/` (stub adapters; order,
fallback, stale-serve, budget behavior) → `tests/tools/` (envelope shape end-to-end with stubbed
chains). Two autouse conftest fixtures do the heavy lifting: `isolated_cache` (fresh per-test
diskcache under tmp_path, no Redis) and `no_live_credentials` (blanks every API key + scraper
toggle so a developer's `.env` can never cause live HTTP in tests). CI gates: ruff + pytest with
`--cov-fail-under=84` on Python 3.11/3.12/3.13, plus pip-audit, bandit, gitleaks, and
`scripts/check_release_build.py` (verifies dist artifacts exclude sensitive paths).

---

## 4. Key design decisions and their reasoning

1. **Everything routes through `FallbackChain`** (ADR-0005). Free-tier APIs die routinely; the
   product promise is "the tool always answers something honest." The envelope's `meta.source` /
   `is_stale` / `fallback_used` lets the AI adapt its wording ("as of ~4 minutes ago…").
2. **Budget tokens consumed only after success** (peek before, consume after). A failed or
   missing-key call must not burn quota — CricAPI's 100/day dies for *everyone* when exhausted.
3. **429 is never retried on quota-capped APIs** (`get_json`), but IS retried on burst-limited
   no-quota sources (`get_json_burst`, OpenF1 only). Getting this backwards burns 3× quota on
   guaranteed failures.
4. **Adapters constructed unconditionally; credentials checked at fetch time.** Keyless installs
   still see every adapter in `sportiq_health()` and the chain walks past them silently.
5. **NotFoundError vs AllSourcesFailedError distinction in the chain:** only when *every* adapter
   that ran raised `NotFoundError` (none skipped for budget, none failed otherwise) does the chain
   raise `NotFoundError` → tool returns `NOT_FOUND`. Anything else is `ALL_SOURCES_FAILED`.
6. **Empty upstream success = failure** (api_football lesson, 2026-07-03): the free plan returns
   `[]` for WC 2026, which — if treated as success — gets cached for 30 min and *shadows* the
   working sources below. Adapters must raise `NotFoundError` on empty payloads.
7. **Pure-ASGI middleware only on the HTTP transport.** Starlette's `BaseHTTPMiddleware` buffers
   SSE and silently breaks MCP streamable-HTTP. This was learned the hard way; both existing
   middlewares carry warning comments.
8. **Docstrings are production interface** (fastmcp-conventions): first line = tool selection
   signal for the model, `Args:` block = parameter filling, enforced by `test_param_docs.py` and
   surfaced into schemas by `core/param_docs.py`.
9. **Frozen Elo seed, opt-in live walk** (D1 finding): re-tuning the seed against WC 2022
   backtests was abandoned — the hand-set seed embeds hindsight the tuned one can't match. Never
   re-tune the seed lineage; `elo_live` walks it forward from real results instead.
10. **No hand-curated player data** (repo-analysis constraint): datasets must be regenerable by
    script from a public source (`scripts/build_*.py`), or they don't ship.
11. **Free edition with paid edition preserved:** the entitlement-gate cluster
    (`core/license.py`, `core/pro_middleware.py`, `SUBSCRIPTION_REQUIRED` code) was deleted in
    v0.3.0 but is fully recoverable from tag `v0.2.3`. `LegacyKeyPathMiddleware` is the only
    surviving trace, kept so sponsor connectors configured with `/u/<key>/mcp` URLs don't 404.

---

## 5. Critical paths — what's load-bearing vs. safe

**Maximum blast radius (change with tests + review, never casually):**
- `src/sportiq/core/fallback.py` — every one of the 44 tools flows through it.
- `src/sportiq/core/tool_response.py` + `errors.py` — the envelope contract every client depends on.
- `src/sportiq/core/cache.py`, `ratelimit.py`, `http.py` — quota protection; a bug here can
  exhaust a shared free-tier key for all users of the hosted instance.
- `src/sportiq/server.py` — the uvx contract (`main()` + `[project.scripts]`) and the HTTP
  transport wiring. Breaking `main()` bricks every installed client config.
- `src/sportiq/{sport}/chains.py` — adapter order IS the product behavior; TTLs are policy
  (`.claude/rules/caching-policy.md`), not tuning knobs.
- `src/sportiq/football/data/*.json` — regenerated by `scripts/build_*.py`, never hand-edited.
  `wc2026_bracket.json` encodes the official FIFA format; an error here silently skews every
  bracket simulation.
- `pyproject.toml` — the sdist exclude list + `check_release_build.py` patterns are the only
  thing keeping private planning docs out of PyPI artifacts.

**Medium (behavior-visible but locally contained):** individual adapters, individual tools,
model files (each has focused unit tests).

**Safe to change casually:** `docs/wiki/` pages, `README.md`, `scripts/dashboard.py` (local-only
analytics), `launch/` marketing copy, wiki lint tooling.

---

## 6. Surprises and non-obvious traps (the ones that already bit)

1. **`uv sync` alone UNINSTALLS the dev and analytics extras.** Always
   `uv sync --extra dev --extra analytics`. Has bitten twice.
2. **`BaseHTTPMiddleware` breaks MCP streamable-HTTP** (SSE buffering). Pure ASGI only on `/mcp`.
3. **Football fixture `status` strings differ per adapter** (api-football: `FT`/`AET`/`PEN`;
   football-data.org: `FINISHED`). Gate finished-detection on the status set, never on
   "scores present". Preserve provider match ID, stage/round, and explicit winner: stage must
   distinguish a same-pair knockout rematch from its group match, and `PEN` may be score-level.
4. **api_football free plan returns empty (not error) for uncovered seasons** — and an empty
   success would poison the cache for 30 min. The guard raises `NotFoundError`; keep it.
5. **Version lives in three places:** `pyproject.toml` (source of truth; `__init__.__version__`
   now reads package metadata dynamically after drifting two releases), and `server.json` (MCP
   registry manifest — manual bump, was once 2 minors behind). `mcpb/manifest` also references it.
6. **OpenF1 401s recent-season (2025+) data without an API key**; historical 2023–24 is free.
   Build scripts skip-with-warning; the runtime adapter is unaffected so far.
7. **Registration order in `server.py` ≠ import order.** Imports are alphabetical (ruff isort);
   only the `register_*` calls carry the football → F1 → cricket relevance order.
8. **Cassette recording is manual-only.** CricAPI fixtures come from its docs page, RapidAPI from
   the portal's sample tab, scrapers from one dev-time live fetch (scrub Set-Cookie first).
9. **The hosted deployment runs diskcache, not Redis** (zero-spend rule) — per-instance cache,
   per-instance rate-limit counters. Hosted limit math therefore requires max-instances=1;
   this branch documents but did not deploy that setting. See GAPS.md #2/#5 and ADR-0012.
10. **CBC must exist on PATH** for the Dream11 solver — `brew install cbc` (macOS),
    `apt-get install coinor-cbc` (CI/Docker do this explicitly).
11. **Coverage gate lives in the CI command, not pyproject `addopts`** — deliberately, so partial
    local runs don't fail. Don't "fix" that.
12. **The repo root is full of local-only business docs** (`launch/`, `sponsor-ledger.md`,
    `monetization-*.md`, `v2*.md`, `free-rollback-plan.md`, …). They are variously gitignored or
    committed-but-sdist-excluded. Never reference them from shipped code, never let a new one leak
    into dist (check `check_release_build.py`), and never commit `step*.md`.
13. **DNS-rebinding protection is intentionally disabled** on the HTTP transport — Cloud Run's
    host headers trip it, and the perimeter is Cloud Run's problem. Not a security hole to "fix".
14. **`docs/log.md` is a hard-rule journal** — every meaningful operation appends an entry.
    If you're wondering "what happened recently", read its tail before anything else.
