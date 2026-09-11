# grokbot1 — INDEX + safety

| Field | Value |
|---|---|
| Repo | `sportiq-mcp (Ninjabeam20/SportIQ-MCP)` |
| Branch | `bot` |
| `main` SHA (do not move) | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` |
| `bot` SHA at original plans | `dfe9bf43b045c5a8a3c1f00aa711aae38c02e219` |
| Recheck date | 2026-09-11 |
| Recheck model | `cursor-grok-4.6-high` (NORMAL, `fast=false`; `originalModelName` did **not** contain `fast`) |
| Recheck method | Static read of tree on `bot`; no pytest run this pass; no app code |
| Scope this commit | Plans only. No production code. |
| Later implementer | Composer 2.5 against **this** spec |

## Goal
Index diagnosis-driven bot-branch work and bind safety before code. This recheck replaces “proven RED on base” with **per-finding status vs the actual `bot` tree**.

## Non-goals
- No merges to `main`
- No Cloud Run / cloudbuild / Dell deploy without an explicit yes in that message
- No live paid sports API calls in unit tests (`respx` + `tests/fixtures/**` only)
- This recheck: no app code, no wiki/GAPS edits, no Elo retune, no Dockerfile/cloudbuild edits

## Recheck notes (2026-09-11)

Original grokbot1–4 over-claimed. Several items are **already GREEN** on `bot` (same code as `main` plus the first plans commit). Composer 2.5 must **not** rewrite those paths. Residual work is listed under **Ranked remaining work**.

Environment vs original operating-mode text:

| Original claim | Recheck |
|---|---|
| Work in `.worktrees/bot` | **Missing.** This repo has no `.worktrees/`. `.gitignore` only ignores `.claude/worktrees/`. Implement **on branch `bot` in the normal checkout**. |
| Leave dirty `audit-fixes` intact | **No `audit-fixes` ref** on origin. Ignore. Do not create it. |
| Base SHA `5cfa12f` | That is **`main`**, still unchanged. `bot` HEAD at recheck start was `dfe9bf4` (plans commit on top of `main`). |
| “Never push” | Binding for **impl vs production**. This recheck session may commit+push `bot` and open an **unmerged** PR. Composer 2.5 still: no merge to `main`, no deploy. |

## Safety (binding)

- Implement only on branch `bot`. Never merge to `main`. Never deploy unless the user explicitly says yes in that message.
- No live scrape / live LLM / live SSH / live paid API hammering unless the user explicitly asks.
- Prefer offline fixtures under `tests/fixtures/**`. NEVER call live APIs in tests.
- TDD: failing test first (RED) → minimal fix (GREEN) → tidy. Do not refactor adjacent working code.
- Do not stage `.env`, credentials, tokens, secrets, `docs/log.md` (gitignored), `*.local.md`, `docs/graphify/`.
- Models stay pure (no I/O, no envelopes). Envelopes only at tool layer via `error_envelope` / `tool_response`. INTEL tools that already splat `staleness_meta` into a hand-built success `meta` may keep that pattern — do not convert them to per-tool Pydantic models.
- Every tool still routes through a `FallbackChain`. Never call an adapter from a tool.
- Scrapers stay opt-in (`SPORTIQ_ENABLE_NDTV` / `SPORTIQ_ENABLE_CRICBUZZ`). Do not enable them in tests or the shipped default.
- Elo seed stays frozen. Do not retune. Do not set `K_SERVICE` anywhere.
- Local cache is `diskcache` without Redis — that is healthy. Do not add Redis health-fail.

## Composer 2.5 contract (later impl — do not do it in this recheck)

1. Read **this file + the matching grokbot2/3/4 section** before touching a finding.
2. Implement **only residual RED / residual LATENT** rows. GREEN rows = add a missing regression test if grokbot2/3 names one; otherwise skip.
3. One finding at a time, in the ranked order below. Do not bundle unrelated refactors.
4. Exact test names in grokbot2–4 are the RED tests to add. Copy existing test style (`test_<unit>_<behavior>_<condition>`).
5. If a GREEN path already has the named test, **do not rewrite the implementation** to make the new test pass a different way.
6. Do not swallow unexpected exceptions into envelopes (telemetry must still re-raise). Envelope-wrap only `AllSourcesFailedError`, `NotFoundError`, `InvalidInputError` (and existing sport-tool patterns).
7. After each finding: targeted pytest cluster in grokbot4. Do not require full-suite locally if a cluster is GREEN; CI coverage gate stays CI-only.
8. Stop if the user has not said yes and the change would deploy, hit a live paid API, or merge to `main`.

## Plan map
| File | Theme |
|---|---|
| `grokbot1.md` | INDEX + safety + recheck matrix |
| `grokbot2.md` | Tier A — crash / uncaught exception classes |
| `grokbot3.md` | Tier B — empty-200 cache poison + CricAPI unwrap + IN_PLAY |
| `grokbot4.md` | Docs hygiene + verification |

## Status matrix (recheck)

| ID | Theme | Status on `bot` | Composer 2.5 |
|---|---|---|---|
| SQ-A1 | pit compound / rainfall | **RESIDUAL RED** — `TypeError`/`ValueError` on dirty telemetry | Fix model + tests |
| SQ-A2 | gather envelopes | **MOSTLY GREEN** — F1/football intel already `return_exceptions=True` | Verify-only; do not wrap unknown exceptions |
| SQ-A3 | cricket NotFound | **CHAIN GREEN; RAW LATENT** — 4 cricket RAW tools miss `except NotFoundError` | Copy scorecard pattern |
| SQ-A4 | Dream11 CBC | **MOSTLY GREEN** — infeasible already `InvalidInputError`; missing CBC still leaks | Catch solver/PATH failure |
| SQ-A5 | value-bet odds | **PARTIAL** — `None` skipped; `odds <= 0` raises `ValueError` in `find_value` | Skip illegal prices |
| SQ-A6 | form-trends int | **PARTIAL** — `int(goals)` can `ValueError`; also ignores `status` | Coerce/skip; share finished-status with B3 |
| SQ-B1 | empty-200 poison | **PARTIAL** — api_football + CricAPI failure envelopes GREEN; football-data.org empty still success | Raise `NotFoundError` on empty FD.org fixtures/standings |
| SQ-B2 | CricAPI unwrap | **GREEN** — `_unwrap` + tests + finding | Verify-only |
| SQ-B3 | IN_PLAY honesty | **PARTIAL** — `results_state` GREEN (`test_in_play_score_not_locked`); `form_trends` still score-gated | Align form_trends; do not invent cricket IN_PLAY enum |
| SQ-D1 | findings/wiki | After impl | Honest bot status; no “fixed in prod” |
| SQ-V1 | verification | After impl | pytest clusters + SHA gates in grokbot4 |

## Ranked remaining work (impl order)

1. SQ-A1 pit dirty telemetry
2. SQ-A5 skip non-positive odds in `find_value`
3. SQ-A4 missing CBC → `InvalidInputError`
4. SQ-A6 + SQ-B3 form_trends finished-status + non-int goals (same file; one PR-sized change)
5. SQ-A3 cricket RAW `NotFoundError` catch
6. SQ-B1 football-data.org empty payload
7. SQ-A2 / SQ-B2 verify-only tests if still missing
8. SQ-D1 wiki/GAPS honesty + SQ-V1

## Pin verification (paths exist on `bot` @ `dfe9bf4`)

| Pin | Exists? |
|---|---|
| `src/sportiq/f1/models/pit_strategy.py` | yes |
| `src/sportiq/core/tool_response.py` | yes |
| `src/sportiq/core/fallback.py` | yes (`NotFoundError` walk ~L158–224) |
| `src/sportiq/core/errors.py` (`NotFoundError` ~L52) | yes |
| `src/sportiq/core/value_bet.py` | yes (canonical; football re-exports) |
| `src/sportiq/football/models/value_bet.py` | yes (re-export only) |
| `src/sportiq/football/models/form_trends.py` | yes |
| `src/sportiq/football/models/results_state.py` | yes (`_FINISHED_STATUSES`, `_is_finished`) |
| `src/sportiq/cricket/models/dream11_solver.py` | yes |
| `src/sportiq/cricket/adapters/cricapi.py` (`_unwrap`) | yes |
| `src/sportiq/cricket/tools.py` | yes |
| `src/sportiq/f1/intel_tools.py` (gather) | yes — **better pin than `server.py` for SQ-A2** |
| `src/sportiq/core/tool_telemetry.py` | yes — logs then **re-raises** |
| `docs/wiki/models/pit-strategy.md` | yes |
| `docs/wiki/findings/cricapi-envelope-leak.md` | yes (already documents the fix) |
| `tests/fixtures/cricapi/` | yes (8 json files) |
| `tests/chains/test_chain_not_found.py` | yes |
| `.worktrees/bot` | **no** |
| `docs/log.md` | gitignored; do not commit |

## Checklist

- [x] Recheck grokbot2–4 against tree (this pass)
- [x] Composer 2.5: read grokbot2–4 before coding
- [x] Worktree/branch == `bot`; `main` SHA unchanged
- [x] No Cloud Run / merge to `main` / deploy
