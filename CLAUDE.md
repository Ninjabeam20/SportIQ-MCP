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

## Common commands

- `uv sync` — install deps
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
