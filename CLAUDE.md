# sportiq-mcp

MCP server exposing AI-callable tools across FIFA World Cup 2026 football, Formula 1, and IPL cricket. The differentiator is the intelligence layer: `football_simulate_bracket` (Monte Carlo with Poisson xG), `f1_predict_pit_strategy` (tyre degradation model on OpenF1 telemetry), `cricket_build_dream11_team` (PuLP constraint solver). Raw data tools are table stakes — the three flagships are the product. Order of relevance everywhere (headings, lists, tool registration): football → F1 → cricket.

## Who I Am

Utkarsh — software engineer building an automated job application pipeline. Familiar with the full stack here. Skip the basics; flag the gotchas.

## Collaboration Rules

1. **Ask, do not assume.** If anything is unclear, ask before writing a single line. No silent guesses about intent, architecture, or requirements.
2. **Simplest solution first.** No abstractions or flexibility I did not explicitly request.
3. **Do not touch unrelated code.** If a file or function is not part of the current task, leave it alone even if you think it could be improved.
4. **Flag uncertainty explicitly.** If you are not confident about an approach, say so before proceeding.
5. **No filler openers.** Match response length to task complexity. Show options before significant work. Admit uncertainty before inventing facts.
6. **Only modify lines directly related to the task.** Ask before rewriting existing working code. Confirm before deletes, overwrites, migrations, or irreversible commands.
7. **Hard stops for production:** deploys, schema changes, external API calls, and anything irreversible need an explicit "yes" in the current message.
8. **End every coding task with:** files changed, what was modified per file, what was intentionally not touched, and any follow-up needed.
9. **Default reply structure.** End every task/answer with three short, plain-language sections — **1. What I did**, **2. What I'm unsure about / recommend**, **3. What I need you to do**. Keep it brief; cut background/sources unless asked; if a section is empty say "nothing." For coding tasks, fold the Rule #8 files-changed detail into section 1.

## Stack (frozen)

- **Runtime:** Python 3.11+
- **Packaging:** `uv` + `pyproject.toml`; ship via `uvx`
- **MCP framework:** `mcp` SDK with FastMCP (decorator API)
- **HTTP:** `httpx` (async) + `tenacity` (retry/backoff)
- **Schemas:** `pydantic v2` + `pydantic-settings`
- **Cache:** `redis` primary, `diskcache` automatic fallback
- **Solver:** `PuLP` (Dream11 ILP via CBC)
- **Stats:** `scipy` (Poisson) + `numpy` (vectorized Monte Carlo)
- **DataFrames:** `pandas` (F1 lap-time fits)
- **F1 (optional, lazy-imported):** `fastf1`
- **Testing:** `pytest` + `pytest-asyncio` + `respx` (no live API hits in CI)
- **Lint/format:** `ruff`
- **Logging:** `structlog` (JSON in prod, pretty in dev)
- **Inspector:** `@modelcontextprotocol/inspector` (via npx)

**Deliberately excluded:** OR-Tools, SQLAlchemy, FastAPI, OpenTelemetry, any database other than Redis/diskcache.

## Hard rules (project-specific)

- Every tool MUST route through a `FallbackChain` (see `.claude/rules/fallback-contract.md`). Never call an adapter directly from a tool.
- Every tool MUST return the `{data, meta}` envelope on success and the error envelope on failure (see `.claude/rules/error-envelope.md`).
- NEVER call live APIs in tests. Use `respx` cassettes from `tests/fixtures/`.
- NEVER bypass the cache to "make sure data is fresh." If TTL is wrong, change the TTL.
- NEVER commit `.env`, `*.local.md`, or `docs/graphify/`.
- Wiki pages MUST have YAML frontmatter (see `.claude/rules/wiki-conventions.md`).
- Append a `## [YYYY-MM-DD] op | subject` entry to `docs/log.md` after every meaningful operation (ingest, decision, lint, release, tool-added, adapter-added, finding-filed).
- **Local dev assumes `diskcache`, not Redis.** Do not write code, tests, or health checks that require a running Redis daemon. `core/cache.py` auto-detects and downgrades to `diskcache` when `REDIS_URL` is unset or the daemon is unreachable. `diskcache` is a healthy state for local dev — do not flag it as degraded.
- **`pyproject.toml` MUST declare `[project.scripts] sportiq-mcp = "sportiq.server:main"`** and `server.py` MUST expose a `main()` function that calls `mcp.run()`. This is the uvx contract — do not break it.
- **Scrapers are opt-in.** Adapters whose data source has a no-scraping ToS (currently: NDTV Sports, Cricbuzz) MUST be disabled by default in the shipped package. They register in the chain but are skipped unless the operator explicitly opts in via env flag (`SPORTIQ_ENABLE_NDTV=1`, `SPORTIQ_ENABLE_CRICBUZZ=1`). See ADR-0007.
- **Adapter constructors don't raise on missing credentials.** Adapter is constructed unconditionally so it appears in `sportiq_health()`. Missing keys cause `healthcheck() → False` and `fetch() → MissingCredentialsError`. The chain treats this as a normal failure and walks past it.

## Context navigation

When you need to understand a domain question (scoring rules, API quirks, model derivations, fallback decisions):

1. ALWAYS read `docs/index.md` first. It lists every wiki page with a one-line description.
2. Open the 1–2 wiki pages the index points to. Do NOT grep the whole tree.
3. Only read raw source files in `docs/raw/` if I explicitly say "read the raw file" or the index points there.
4. For code questions spanning >3 modules, run `/graphify .` first and query the graph instead of reading raw files.
5. Hosting/product progress: `docs/wiki/findings/product-hosting-arc.md` (Dell live; GCP gone).

## Common commands

- `uv sync --extra dev --extra analytics` — install deps. ALWAYS pass both extras: a plain `uv sync` uninstalls them (dev = pytest/ruff, analytics = the GCP libs `scripts/dashboard.py` needs) — this has bitten twice.
- `uv run pytest` — run all tests (must pass before any commit)
- `uv run python -m sportiq.server` — local dev server
- `npx @modelcontextprotocol/inspector uvx --from . sportiq-mcp` — verify MCP schema
- `/project:add-tool <name>` — scaffold a new tool end-to-end
- `/project:add-adapter <chain>` — add a data source to a fallback chain
- `/project:ingest <path>` — process a file in `docs/raw/` into the wiki
- `/project:file-finding` — file the current chat finding into `docs/wiki/findings/`
- `/project:update-wiki` — run lint pass (contradictions, orphans, gaps, stale claims)
- `/project:inspect` — launch MCP inspector
- `/project:release` — version bump → build → publish to PyPI

## Deep-context docs

- **`PROJECT.md`** — full architecture narrative: what this is, stack rationale, the
  FallbackChain data flow, key design decisions (ADR summaries), load-bearing vs. safe-to-change
  files, and every gotcha that has already bitten. Read it before any change touching `core/`.
- **`GAPS.md`** — honest severity-ordered audit of known weaknesses, each with file paths and a
  single-task-scoped fix. Check it before "fixing" anything that looks wrong — several apparent
  bugs are documented accepted trade-offs (its final INFO section lists them).
- **`docs/wiki/findings/product-hosting-arc.md`** — GCP → paid → free on GCP → home server.
  Check it when hosting/product history is confusing. Task 9 GCP teardown is done (2026-09-02).
- Both PROJECT/GAPS are local/internal: excluded from the PyPI sdist (`pyproject.toml`), like the other
  root-level planning docs.

## Conventions (the ones the code actually follows)

- **Layers per sport:** `adapters/` (I/O, one class per source+shape) → `chains.py`
  (module-level `FallbackChain` singletons) → `tools.py` (RAW) / `intel_tools.py` (INTEL, may
  call `models/`) → `models/` (pure functions, no I/O). Never skip a layer.
- **Tool names:** `{sport}_{verb}_{noun}` snake_case. Return type is always the `Envelope`
  TypedDict from `core/tool_response.py` — this is the sanctioned exception to
  "Pydantic models preferred" (see its docstring; do not convert tools to per-tool models).
- **Error handling in tools:** catch `AllSourcesFailedError` (and `NotFoundError` where the
  chain can raise it — copy the pattern in `cricket/tools.py:71`) → `error_envelope(...)`.
  Never a bare `{"ok": False}`, never construct envelopes by hand.
- **Multi-chain INTEL tools** aggregate freshness with `staleness_meta(*results)` — never
  swallow `is_stale`.
- **Adapters:** use `core/http.get_json()` (`get_json_burst` ONLY for no-quota burst-limited
  sources like OpenF1); raise `MissingCredentialsError` on absent keys (constructor never
  raises); raise `NotFoundError` on empty-but-200 upstream payloads (api_football lesson) so
  the chain walks on instead of caching emptiness.
- **Cache keys:** `sportiq:{sport}:{category}:{readable_args}`; hash with
  `blake2s(digest_size=8)` only for unbounded/user-supplied args.
- **Committed data files** (`src/sportiq/*/data/*.json`) are generated by `scripts/build_*.py`
  from public sources — regenerate, never hand-edit. No hand-curated player data, ever.
- **Test names:** `test_<unit>_<behavior>_<condition>`; four layers under
  `tests/{unit,adapters,chains,tools}/`; respx cassettes in `tests/fixtures/{source}/`,
  re-recorded manually only.
- **Log discipline:** `docs/log.md` is the project journal — read its tail to learn recent
  history; append after every meaningful operation (hard rule above).

## Gotchas (looks like it should work one way — doesn't)

- **HTTP middleware on `/mcp` must be pure ASGI.** `BaseHTTPMiddleware` buffers SSE and breaks
  MCP streamable-HTTP. See `core/path_compat.py` / `core/client_info.py` for the pattern.
- **HTTP transport is stateless** (`mcp.settings.stateless_http = True`, HTTP branch of
  `server.py` only). No `Mcp-Session-Id`, so an in-place `docker compose up --build` on the
  home server does not strand live connectors. stdio/uvx is unaffected. Keep
  `json_response` **False** — SSE framing is how tool results stream. This is a plain
  FastMCP setting on `mcp` 1.29.0; it does NOT require SDK v2.
- **Don't call `mcp.run("streamable-http")` in the HTTP branch** — it rebuilds the Starlette
  app and drops the middlewares. `server.py` builds the app manually; keep it that way.
- **Registration order ≠ import order** in `server.py`: imports stay alphabetical (ruff isort);
  only the `register_*` calls carry football → F1 → cricket relevance.
- **Football fixture `status` differs per adapter** (api-football `FT`/`AET`/`PEN` vs
  football-data.org `FINISHED`). Gate finished-detection on the status set, never on
  "scores present".
- **Never retry 429 on quota-capped APIs** — that's why `get_json` and `get_json_burst` are
  separate. Picking the wrong one burns 3× quota on guaranteed failures.
- **Version lives in 3 places:** `pyproject.toml` (truth), `__init__.__version__` (dynamic —
  leave it), `server.json` (MCP registry). `scripts/check_release_build.py` fails CI if
  `server.json` drifts. FastMCP 1.29 does not take `version=`; `server.py` binds
  `mcp._mcp_server.version = __version__` so initialize reports SportIQ, not the SDK.
- **Coverage gate is in CI only** (`--cov-fail-under=84` in `test.yml`), deliberately not in
  pyproject `addopts` — don't "fix" that; partial local runs must be able to pass.
- **CBC binary must be on PATH** for the Dream11 solver (`brew install cbc` /
  `apt-get install coinor-cbc`).
- **OpenF1 401s 2025+ seasons without a key**; 2023–24 stays free. Build scripts skip-with-warn.
- **The Elo seed is frozen** (D1 finding) — never re-tune it; `SPORTIQ_FOOTBALL_LIVE_ELO=1`
  walks it forward from real results instead.
- **sdist safety is an allowlist** (`pyproject.toml` `[tool.hatch.build.targets.sdist] include`
  + `scripts/check_release_build.py`). New root files are excluded by default. Do not revert
  to a blocklist.
- **`/u/<key>/mcp` paths must keep working** (`core/path_compat.py`) — sponsor connectors from
  the paid era are configured with them.
- **Production live is home-server Compose.** Repo-root `docker-compose.yml` joins
  Docker network `apps`, `container_name: sportiq`, **no** `ports:`. Plan:
  `docs/superpowers/plans/2026-08-13-home-server-migration.md`. Task 9 (2026-09-02)
  deleted Cloud Run, `sportiq-keepwarm`, and Artifact Registry. `cloud.md` is
  historical. Always-on idle: `restart: unless-stopped`; no keep-warm cron on the
  Dell; no auto-sleep. Project `sportiq-mcp-prod` is `DELETE_REQUESTED` (billing
  unlinked 2026-09-02).
- **Never set `K_SERVICE` on the Dell.** That flag means Cloud Run and would trust spoofable
  `X-Forwarded-For`. Home-server Compose sets `SPORTIQ_TRUST_CLOUDFLARE=1` so 429s key on
  `CF-Connecting-IP`. Leave that env unset on stdio.
- **Live public connector URL** is `https://sportiq.utkarshgupta.org/mcp`. Former
  Cloud Run hosts (`ey2eariulq`, `329580761892`) are gone — do **not** advertise
  `*.run.app`.
- **Dockerfile pins `ghcr.io/astral-sh/uv:0.12.6` and installs with `uv export --frozen`
  then `uv pip install --system`.** Do not revert to `:latest` (`uv pip install --frozen`
  is not a pip-interface flag) or unpinned `pip install ".[f1]"`. `mcp` is `>=1.27.2,<2`
  — 2.0.0 removes `mcp.server.fastmcp`. Do not combine the home-server move with SDK v2.

## When you finish a coding task

Per Rule #8, end with exactly this format:

**Files added:**
- `path/to/new/file.py` — what it does

**Files modified:**
- `path/to/existing/file.py` — what changed and why

**Intentionally not touched:**
- `path/to/related/file.py` — could be improved (X) but out of scope for this task

**Follow-up needed:**
- (list, or "none")
