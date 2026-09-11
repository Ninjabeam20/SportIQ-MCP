# order.md — execution order for the unexecuted backlog

> **ACTIVE BRANCH: `bot`** (2026-09-11 reconciliation). Do **not** create `audit-fixes` or rename mid-flight — work on existing `bot` tip `971b16f` (suite **814**).
> Historical: Branch `audit-fixes` (cut from `main` @ `5cfa12f`, 2026-09-05) — superseded for execution.
> Rule: ALL remaining work below happens on **`bot`**. `main` + Dell stay untouched until Phase 7/8 gates pass.
> No pre-existing file does this job: `grok_index.md` has an execution order but Waves A–C are all `[x]` (hosting mission closed 2026-09-02). `BACKLOG.md` is deferred ideas (promotion needs an ADR — NOT scheduled here). `GAPS.md` is severity-ordered but mostly RESOLVED. This file sequences the **2026-09-05 full-repo audit findings** (previously read-only, none executed) plus the small GAPS/git-hygiene leftovers.
> 2026-09-05 sweep: every `*.md` outside `website/node_modules`, `.venv`, `.git` was scanned for unimplemented plans. Phases 1–6 hold the scheduled work; **Appendix A** records everything verified DONE/STALE (so nothing is unaccounted for); **Appendix B** holds deferred items that need a decision/ADR before they may be scheduled. `done/` files are archived history — verdicts about them are recorded here, the files themselves are left untouched.
> Governing correction source: **`muse.md`** (verified 2026-09-05 re-read of the audit against the tree — "follow this file, not the chat"). It confirms most phases below but corrects nine points, all folded in: `Exception` (never `BaseException`); F1 gather paths the audit missed; selective OpenF1 raises; skill-not-code scoring alignment; `SECURITY.md` already current (do not rewrite); `simulate_group()` is used by tests (do not delete); gitignored docs skipped by default; `build_accumulator` needs no guard; F1 TTLs stay in code. Where this file and the raw audit disagree, `muse.md` wins.
> Branch note: `muse.md` suggested `fix/audit-envelope-and-empty-payloads`; historical live branch was **`audit-fixes`**. **2026-09-11: ACTIVE BRANCH is `bot`** — do not create/rename to audit-fixes.

## Agent instruction (binding on every worker, human or agent)

1. Work ONLY on branch **`bot`** (was `audit-fixes`). `main` + Dell stay untouched until Phase 7/8 gates pass with an explicit `yes`.
2. Follow the phase order below (0 → 8). If you believe a better order exists, state it + why in chat and update this file BEFORE reordering — never silently work out of order.
3. Keep the Execution checklist current as you go: tick `[x]` only when the change is in the tree WITH its tests green; the Status column is the single source of truth for what remains.
4. Before touching code, read `muse.md` §0 (hard rules) + §7 (12 do-not-regress patterns). Where this file and the raw audit disagree, `muse.md` wins.
5. Append to Notes (never rewrite history) on every meaningful step: what landed, test evidence, what is next.

## Source inventory (what feeds this order)

- Audit 2026-09-05: HIGH/MED/LOW code bugs + stale docs (none executed yet).
- `GAPS.md` leftovers: #10 OPEN (LOW, defer), #13 PARTIAL (server wiring test exists, scripts untested), #5 wording drift.
- Full-markdown sweep 2026-09-05: `launch/` (01–10 + README + listing-copy), `v3.md`, `BACKLOG.md`, `done/` (`remaining.md`, `remaining2.md`, `remaining3.md`, `update.md`, `review-phase1-cleanup.md`, `v2c-provider-keys-plan.md`, `fable_test.md`, `fable_ultimate.md`, `step5/6/8.md`), `grok_changes1–13.md` + `grok_index.md`, `docs/superpowers/plans/*`, `dev.md`, `sep.md`, `gcp.md`, `muse.md`, `grok_agent.md`, `website/website.md`, `website/CLAUDE.md`, `API-KEYS-AND-SETTINGS.md`, `docs/raw/2026-05-30-step9-test-matrix.md`. Each file's verdict lives in Appendix A/B.
- Git state at branch cut: `M .gitignore` (adds `muse.md`, safe to carry); untracked `gcp.md`, `sep.md`, `sportiq-analytics-dashboard*.png`, `.playwright-mcp/` (need ignore-or-track decision).
- Explicitly NOT scheduled: `BACKLOG.md` post-v1 candidates, GAPS #10 Redis re-probe (no Redis exists), any re-tuning of the frozen Elo seed, Appendix B deferred items (all need a decision first).

## Phase 0 — safety (DONE)

- [x] Create branch `audit-fixes` (carries the `M .gitignore` change; untracked files stay as-is). **Historical** — ACTIVE BRANCH now `bot`.
- [x] Confirm clean baseline on branch: `uv sync --extra dev --extra analytics && uv run pytest -q` green before touching code. Evidence 2026-09-11: bot tip `971b16f` suite **814** green.

## Phase 1 — crash paths (envelope contract). Do first: smallest diffs, biggest reliability win. One commit per bullet, run affected tests each time.

- [x] 1a. `src/sportiq/cricket/tools.py:35,145,173,206` — add `NotFoundError` to `cricket_get_live_matches` / `get_schedule` / `get_squad` / `get_live_odds` (copy `tools.py:71` pattern). Tests: `tests/tools/test_cricket_raw_tools.py`, `tests/tools/test_odds_tools.py`. **DONE** `13e2104` (suite 814).
- [ ] 1b. Gather re-raises → envelope (use `Exception`, NEVER `BaseException` — it swallows `CancelledError`/`KeyboardInterrupt`). Football `src/sportiq/football/intel_tools.py:422-427` (`raise odds_r` / `raise groups_r`); F1 `src/sportiq/f1/intel_tools.py:98-99,106-107` (tyre-deg gather) + `:390-409` (pit-strategy `raise laps_r`/`stints_r`/`weather_r` — missed by the original audit). Pattern: chain-error handling just above those lines. Tests: gather returns generic `RuntimeError` → `error.code == "ALL_SOURCES_FAILED"`, never a raise (`tests/tools/test_odds_tools.py`, `test_football_tools.py`, `test_f1_intel_tools.py`). Do not touch `_maybe_nudge_single` (already degrades). **PARTIAL/CONFLICT** — original envelope work superseded in part by grokbot R7 (`971b16f`): race-pace/player-matchup RE-RAISE unknowns. Tick only parts matching current bot; do not force full tick. (2026-09-11).
- [x] 1c. `src/sportiq/f1/models/pit_strategy.py:51,66` — `None`-compound guard + unknown-compound fallback to MEDIUM. Tests: `tests/unit/test_pit_strategy.py`. **DONE** `13e2104` (suite 814).
- [x] 1d. `src/sportiq/cricket/models/dream11_solver.py:128,135` — catch `PulpSolverError` (missing CBC) → `InvalidInputError("solver unavailable")`; validate C/VC instead of bare `next()`. Tests: `tests/unit/test_dream11_solver.py`. **DONE** `13e2104` (suite 814).
- [x] 1e. Sim-model errors → `INVALID_INPUT` at the tool boundary (models stay raising — they are pure). Catch `except (ValueError, KeyError)` in `football_simulate_group` (~261 `simulate_group_stage`), `football_simulate_bracket` (~323 `simulate_tournament`), `football_knockout_path` (covers malformed draw, unseen third-combo `KeyError`). Tests: `tests/unit/test_group_sim.py`, `test_bracket_sim.py`, `test_bracket_data.py`. Skip: `build_accumulator` guard (parlay.py is defensive — overstated) and `simulate_group()` deletion (used by unit tests — do not delete). **DONE** 2026-09-11 on `bot` — tool catches + 4 tool-level tests in `tests/tools/test_football_tools.py` (malformed draw ×3, KeyError combo ×1); suite 824 green.
- Gate: `uv run pytest tests/tools tests/unit/test_pit_strategy.py tests/unit/test_dream11_solver.py tests/unit/test_group_sim.py tests/unit/test_bracket_sim.py -q` + `ruff check`.

## Phase 2 — empty-success shadowing (quota-relevant). Do second: stops caching emptiness that blocks fallbacks.

- [x] 2a. Football: `adapters/api_football.py:90-107` (standings), `:177-195` (scorers), `adapters/football_data_org.py:30-132` (fixtures/standings/scorers), `adapters/openfootball.py:28-48`, `adapters/static_seed.py:42-50` — raise `NotFoundError` on empty payloads (mirror fixtures/squad guards). Fix `football_data_org.py:93-107` TeamStats (wrong endpoint / ID space — raise or drop from chain). **DONE** 2026-09-11 on `bot`: api_football standings/scorers empty (`77bef8f`/`b395f15`) + TeamStats empty-guard; FD fixtures/standings/scorers empty + TeamStats always-raise (wrong endpoint); openfootball empty-matches raise; static_seed groups/fixtures missing-file raise (squad terminator untouched); suite 824 green.
- [ ] 2b. F1 selective empty raises (`adapters/openf1.py`): laps + stints + drivers raise `NotFoundError` on `[]`; **weather + sessions stay** (valid empty: no-weather session, country filter with no match). `adapters/jolpica.py:15,33` — raise on empty tables; standings `gather(return_exceptions=True)` + partial handling. **DEFERRED / R6 SKIPPED** (2026-09-11) — leave unchecked.
- [x] 2c. `football/adapters/derived_standings.py:26-31` — route via fixtures chain/cache instead of direct adapter `fetch()`. **DONE** 2026-09-11 on `bot`: lazy `football_fixtures_chain.fetch()` (no deadlock — fixtures chain excludes derived); `_derived_standings` registered for health in `chains.py`; chain-routing regression test; suite 824 green.
- Gate: adapter + chain tests (`tests/adapters/test_api_football.py`, `test_football_data_org.py`, `test_openfootball.py`, `test_openf1.py`, `test_jolpica.py`, `tests/chains/`).

## Phase 3 — model/math correctness. Do third: behavior-visible, each isolated.

- [ ] 3a. Player-stat extractor (one fix, three readers): write a single extractor accepting wrapped `{data:{stats}}` AND unwrapped `{stats}`/`{values}` with `playingRole` (CricAPI unwraps in the adapter — rows live at `payload["stats"]`, cassette `tests/fixtures/cricapi/players_info.json`; RapidAPI at `values`, cassette `tests/fixtures/rapidapi/player_career.json`). Wire into `cricket/models/player_matchup.py:30-55`, `cricket/intel_tools.py:334-368` `_t20_career_numbers`, `cricket/models/form_index.py:117-118`. Tests: feed unwrapped cassette shapes → non-`other` matchup when roles/averages exist (`test_player_matchup.py`, `test_form_index.py`, `test_cricket_player_matchup.py`).
- [ ] 3b. (Optional, low impact) `f1/data/points.py:8,14-26` — fastest-lap bonus only when `year < 2025`. Skip if the batch is large.
- [ ] 3c. Dream11 scoring — align the SKILL, not the code: copy values from `docs/wiki/models/dream11-scoring.md` (code `scoring.py` 50→+4, 100→+8, maiden +12 already agrees with the wiki) into `.claude/skills/dream11-scoring/SKILL.md` (still 25/50/75/100 + maiden +8). Do not touch `scoring.py` unless live Dream11 tables are wanted.
- [ ] 3d. (Optional) `f1/models/race_pace.py:62,66` — require `sample_count >= 2`, `faster = None` on `pace_delta == 0`; `tyre_deg.py:93` — document enumerate-index intercept; `group_sim.py:276` — sum-then-round `p_advance`; `theodds.py:60-68` — leave zero-bookmaker events unless trivial (value-bets `events_analysed` counts rated teams, not bookmakers).
- [ ] 3e. (Optional, out of batch 1) `f1/adapters/fastf1_local.py:44,84` — `asyncio.to_thread` for blocking calls; verify `_SESSION_REGISTRY[9877]`; standings loop bound.
- Gate: `uv run pytest tests/unit -q`.

## Phase 4 — meta/staleness/health/TTL alignment. Do fourth: no behavior change, fixes observability.

- [ ] 4a. `football/intel_tools.py:469-473` (include `groups_result`), `f1/intel_tools.py:577` (include stints), `cricket/intel_tools.py:405` (use `staleness_meta`), `cricket/intel_tools.py:678,545` (keep single staleness source, propagate attempts), `f1/intel_tools.py:557,473` (propagate `e.code`/attempts).
- [x] 4b. `football/models/form_trends.py:25-36,50-51` — import `_is_finished` from `results_state.py:123-128` (`FINISHED`/`FT`/`AET`/`PEN`/`AWD`/`WO` + scores present; in-play with live scores must NOT count, `FT` must); coerce goals with try/`continue` instead of bare `int()`. Tests: `tests/unit/test_form_trends.py`. **DONE** `13e2104` + R4 xG (suite 814).
- [ ] 4c. `football/adapters/football_data_org.py:60-61,89-90` — `healthcheck()` returns `bool(settings.footballdata_key)`; `core/health.py:65-68` — report per-minute window too; register `derived_standings` for health; fix `football/chains.py:95,103` squad key `str(team)` normalisation.
- [ ] 4d. TTL doc decisions (code is truth in both): F1 laps/stints 10s/60s live telemetry → update `docs/wiki/chains/f1-laps-chain.md:25`, `f1-stints-chain.md:24`, `docs/index.md:111-112`. Football groups ~1y is INTENTIONAL (static draw seed, still correct post-tournament) → keep code, record the rationale in `docs/wiki/chains/football-groups-chain.md` + `chains.py:88-89` comment (closes step6 A5; `done/remaining.md:59-60` stays as history).
- [ ] 4e. Chain docstring touch: `src/sportiq/cricket/chains.py:4-10` — adapter lists verified correct against code (standings `cricapi → rapidapi` matches; review-cleanup #4 DONE); drop or define the `→ stale-cache` suffix (stale is chain fallback, not an adapter).
- Gate: tool tests + `tests/unit/test_o3_cache_ttls.py`.

## Phase 5 — stale memory/docs. Do fifth: after code settles so docs describe reality.

- [ ] 5a. Tracked steel docs: `AGENTS.md:42,43,47` (`.Codex/rules/` → `.claude/rules/`, copy `CLAUDE.md` paths — do NOT create `.Codex/rules/`), `BACKERS.md:19-21` (donation-only), `PROJECT.md:206` (re-run `pytest --collect-only -q` on the branch, write the ACTUAL number — do not invent), `GAPS.md:157-159` (rewrite: Compose one replica is the pin; `cloud.md:77` max-instances is historical Cloud Run; Redis needed only if a second replica is added), `Dockerfile:35` (comment → Compose sets `PORT=8080`; behavior unchanged), `cloud.md` (one-line stale guard under `## PART 1` only — file banner already exists), `.github/workflows/test.yml:31` (comment "analytics extra is dashboard-only" — preferred over adding the extra). Skip: `SECURITY.md` hosting section (already Dell — verified current).
- [ ] 5b. Wiki nits + index slugs: `docs/index.md:79,80,81,91,92` → `tyre-degradation`, `undercut`, `pit-strategy`, `cricket-win-probability`, fix `head-to-head` pointer. `docs/wiki/data-sources/api-football.md:21` — make the `[[../../../.claude/rules/api-budgets]]` backlink plain text (step6 A6). `docs/wiki/decisions/0007-cricket-fallback-strategy.md:22` — fix the `(CricAPI + CricSheet)` parenthetical (contradicts its own 2026-05-27 Amendment + D3a offline-only reintroduction).
- [ ] 5e. Consistency checklist (steel docs must agree after 5a–5d): tool count 44 in `README`/`PROJECT`/`dev.md`/live `tools/list`; coverage `--cov-fail-under=84` in `test.yml`/`CLAUDE.md`/`AGENTS.md`/`PROJECT.md`; Dell-live + Task-9-done in `CLAUDE.md`/`PROJECT.md`/`GAPS.md`/`README.md:60-63,122`; `server.json` 0.3.2 == `pyproject.toml` 0.3.2; `docs/index.md` slugs == `docs/wiki/` filenames (no orphans); `pyproject.toml` sdist allowlist + `check_release_build.py` green.
- [ ] 5c. Gitignored local docs — DEFAULT SKIP (not shipped; verified). Fix only if explicitly asked: `LEARNING-GUIDE.md`, `dev.md`, `interview_cheatsheet.md`, `interview_preparation_guide.md`, `BACKLOG.md:21`, `API-KEYS-AND-SETTINGS.md:3,81`, `v3.md` counts, `gcp.md`/`sep.md` bodies. (An earlier draft of this file scheduled them; correction per `muse.md`: their staleness is local-only. Consistency-everywhere = tracked files in 5a/5b + `.gitignore` keeping the rest out of the tree.)
- [x] 5d. `core/value_bet.py:60-63` — skip `decimal_odds <= 0` like `None` (one bad bookmaker must not kill the scan); F1 quali `NotFoundError` `sources_tried` (`f1/intel_tools.py:479-483`) + cricket matchup attempts (`cricket/intel_tools.py:678`). Optional: `match_resolver` narrow to chain errors; `core/health.py:65-68` per-minute quota (keep `HealthReport` shape). Do NOT delete `simulate_group()` (used by tests). **DONE** `13e2104` (suite 814).
- Gate: `uv run python scripts/check_release_build.py`, wiki frontmatter lint if available.

## Phase 6 — hygiene (gitignore decision). Do with Phase 5.

- [ ] Commit the carried `M .gitignore` (`muse.md` line) on this branch.
- [ ] Decide untracked: `gcp.md`, `sep.md`, `sportiq-analytics-dashboard*.png`, `.playwright-mcp/`, `muse.md` → append to `.gitignore` OR `git add` intentionally. (Untracked+unignored = accidental-commit risk. `muse.md` is a local briefing, same class as `grok_index.md` — keep it out of the public tree.)
- [ ] `cloudbuild.yaml:16-17` targets deleted `sportiq-mcp-prod` — mark historical in-file; deletion needs explicit yes.

## Phase 7 — verify, push, merge (gated)

- [ ] Full gates on branch: `uv sync --extra dev --extra analytics`, `uv run pytest -q`, `ruff check`, `uv run python scripts/check_release_build.py`.
- [ ] Append `docs/log.md` entry for the batch (note: `docs/log.md` is currently gitignored-working-copy — keep local per ignore rule).
- [ ] Push branch (needs your explicit `yes` in-chat per hard-stop convention for shared-state ops): `git push -u origin bot` (was audit-fixes) — **NO PUSH** per 2026-09-11; local commit only. **DEFERRED / hard stop** — Phase 7 push-to-main UNCHECKED (2026-09-11).
- [ ] Open PR → review → merge to `main`. Tag only if releasing (release flow = `/project:release`, needs explicit yes).

## Phase 8 — deploy + iterate (HARD STOP — needs explicit `yes` in current message)

- [ ] Do NOT run without a fresh `yes`: Dell is production (`restart: unless-stopped`, single replica, no ports). Never `K_SERVICE`, never keep-warm copy. **DEFERRED / hard stop** — Phase 8 deploy UNCHECKED (2026-09-11).
- [ ] Deploy: on Dell, `docker compose up -d --build`, then smoke: `initialize` 200 + `tools/list` 44 + `sportiq_health` diskcache + `football_simulate_bracket(500, seed=42)` sanity.
- [ ] Iterate: file new findings → append to this file's "Notes" → repeat Phases 1–7 per batch.

## Execution checklist (file-level — the tracking table)

Tick `[x]` only when the change is in the tree with green tests. "New" = file to be created. Phases give the order; this table gives the per-file status.

### Phase 0 — baseline

| Status | File | Change |
| :--- | :--- | :--- |
| [x] | (worktree) | `uv sync --extra dev --extra analytics && uv run pytest -q` green baseline on `bot` — **814** @ `971b16f` (2026-09-11) |

### Phase 1 — crash paths

| Status | File | Change |
| :--- | :--- | :--- |
| [x] | `src/sportiq/cricket/tools.py` | 1a: dual `except (AllSourcesFailedError, NotFoundError)` ×4 fns — **DONE** `13e2104` |
| [x] | `tests/tools/test_cricket_raw_tools.py` | 1a: `NotFoundError` → envelope regression tests — **DONE** `13e2104` |
| [ ] | `src/sportiq/football/intel_tools.py` | 1b: gather `Exception` → envelope (422-427); 1e: sim `INVALID_INPUT` catches | **PARTIAL/CONFLICT** vs R7 re-raise (`971b16f`)
| [ ] | `src/sportiq/f1/intel_tools.py` | 1b: gather `Exception` → envelope (98-99, 106-107, 390-409); 4a: staleness + `sources_tried` | **PARTIAL/CONFLICT** vs R7 re-raise (`971b16f`)
| [ ] | `tests/tools/test_odds_tools.py`, `test_football_tools.py`, `test_f1_intel_tools.py` | 1b/1e: `RuntimeError` → envelope tests |
| [x] | `src/sportiq/f1/models/pit_strategy.py` | 1c: `(… or "MEDIUM").upper()` + `TyreCompound` fallback — **DONE** `13e2104` |
| [x] | `tests/unit/test_pit_strategy.py` | 1c: `None` + `"UNKNOWN"` compound tests — **DONE** `13e2104` |
| [x] | `src/sportiq/cricket/models/dream11_solver.py` | 1d: solver-exception → `InvalidInputError`, C/VC validation — **DONE** `13e2104` |
| [x] | `tests/unit/test_dream11_solver.py` | 1d: mocked-solve-failure test — **DONE** `13e2104` |
| [ ] | `tests/unit/test_group_sim.py`, `test_bracket_sim.py`, `test_bracket_data.py` | 1e: malformed-draw/combo tests |

### Phase 2 — empty-success shadowing

| Status | File | Change |
| :--- | :--- | :--- |
| [x] | `src/sportiq/football/adapters/api_football.py` | 2a: standings/scorers empty `NotFoundError` — **DONE** `77bef8f`/`b395f15` + TeamStats empty-guard 2026-09-11 (suite 824) |
| [x] | `src/sportiq/football/adapters/football_data_org.py` | 2a: empty raises — **DONE** `77bef8f`/`b395f15` + TeamStats always-raise 2026-09-11; 4c key-gated healthcheck still open |
| [x] | `src/sportiq/football/adapters/openfootball.py` | 2a: raise on empty `matches` — **DONE** 2026-09-11 (suite 824) |
| [x] | `src/sportiq/football/adapters/static_seed.py` | 2a: raise on missing file (groups/fixtures loaders only; squad terminator untouched) — **DONE** 2026-09-11 (suite 824) |
| [x] | `src/sportiq/football/adapters/derived_standings.py` | 2c: route via `football_fixtures_chain` — **DONE** 2026-09-11 (suite 824) |
| [ ] | `src/sportiq/football/chains.py` | 2a/4c: FD team-stats decision DONE (raise); derived registered for health DONE 2026-09-11; `str(team)` key normalisation still open |
| [ ] | `src/sportiq/f1/adapters/openf1.py` | 2b: laps/stints/drivers raise; weather/sessions untouched | — **R6 SKIPPED** (2026-09-11)
| [ ] | `src/sportiq/f1/adapters/jolpica.py` | 2b: empty-guard + `gather(return_exceptions=True)` |
| [ ] | `tests/adapters/test_api_football.py`, `test_football_data_org.py`, `test_openfootball.py`, `test_football_static_seed.py`, `test_openf1.py`, `test_jolpica.py`, `tests/chains/` | 2a/2b: empty-200 → `NotFoundError`; AF-empty → derived walk-through |

### Phase 3 — model correctness

| Status | File | Change |
| :--- | :--- | :--- |
| [ ] | `src/sportiq/cricket/intel_tools.py` | 3a: shared wrapped/unwrapped extractor in `_t20_career_numbers`; 4a: form-index `staleness_meta`, matchup attempts |
| [ ] | `src/sportiq/cricket/models/player_matchup.py` | 3a: consume extractor output |
| [ ] | `src/sportiq/cricket/models/form_index.py` | 3a: unwrapped `stats` fix |
| [ ] | `tests/unit/test_player_matchup.py`, `test_form_index.py`, `tests/tools/test_cricket_player_matchup.py` | 3a: cassette-shape tests |
| [ ] | `.claude/skills/dream11-scoring/SKILL.md` (+ mirror `.agents/skills/dream11-scoring/SKILL.md` if same content) | 3c: values ← wiki (code untouched) | — leave unless done (2026-09-11)
| [ ] | `src/sportiq/f1/models/race_pace.py`, `f1/data/points.py`, `f1/adapters/fastf1_local.py`, `football/models/group_sim.py:276`, `football/adapters/theodds.py`, `cricket/match_resolver.py`, `core/health.py` | 3d/3e/5d optionals — take only if trivially small |

### Phase 4 — observability

| Status | File | Change |
| :--- | :--- | :--- |
| [x] | `src/sportiq/football/models/form_trends.py` | 4b: `_is_finished` import + goal coerce — **DONE** `13e2104` + R4 xG |
| [x] | `tests/unit/test_form_trends.py` | 4b: in-play-excluded / `FT`-counted tests — **DONE** `13e2104` |
| [ ] | `src/sportiq/cricket/chains.py` | 4e: docstring `stale-cache` touch |
| [ ] | `docs/wiki/chains/f1-laps-chain.md`, `f1-stints-chain.md`, `docs/wiki/chains/football-groups-chain.md`, `src/sportiq/football/chains.py` (comment) | 4d: TTL doc truth + groups-rationale |
| [ ] | `docs/index.md` | 4d (TTL one-liners) + 5b (slugs) |
| [ ] | `tests/unit/test_o3_cache_ttls.py` | 4d: TTL assertions green |

### Phase 5 — docs/memory

| Status | File | Change |
| :--- | :--- | :--- |
| [ ] | `AGENTS.md` | 5a: `.claude/rules/` paths |
| [ ] | `BACKERS.md` | 5a: donation-only |
| [ ] | `PROJECT.md` | 5a: real collect count |
| [ ] | `GAPS.md` | 5a: single-instance pin rewrite |
| [ ] | `Dockerfile` | 5a: `$PORT` comment |
| [ ] | `cloud.md` | 5a: PART 1 stale guard |
| [ ] | `.github/workflows/test.yml` | 5a: analytics-extra comment |
| [ ] | `docs/wiki/data-sources/api-football.md` | 5b: plain-text backlink |
| [ ] | `docs/wiki/decisions/0007-cricket-fallback-strategy.md` | 5b: `:22` parenthetical |
| [x] | `src/sportiq/core/value_bet.py` | 5d: skip `decimal_odds <= 0` — **DONE** `13e2104` |
| [x] | `tests/unit/test_value_bet.py` | 5d: zero-price test — **DONE** `13e2104` |
| [ ] | `docs/log.md` | Phase 7: batch entry (local journal, still required) |

### Phase 6 — hygiene

| Status | File | Change |
| :--- | :--- | :--- |
| [ ] | `.gitignore` | carried `muse.md` line + clutter (`gcp.md`, `sep.md`, `sportiq-analytics-dashboard*.png`, `.playwright-mcp/`, `muse.md`) — commit on branch |

### Explicitly NOT in the checklist (gated / deferred / do-not-touch)

`cloudbuild.yaml` (needs yes) · `SECURITY.md` hosting (current) · Elo seed · `server.py` · scraper gating · `get_json` split · `simulate_group()` · gitignored docs (opt-in) · Dell/GCP (Phase 8 yes) · Appendix B items (need decision/ADR).

## Appendix A — accounted for, NOT scheduled (verified DONE/STALE 2026-09-05)

These files were scanned and contain no executable work for this batch. Recorded here so no markdown plan is unaccounted for. `done/` files are archived history and are left untouched.

- `done/remaining2.md` F3–F8 (form_trends, accumulator, matchup, race_pace, cross-sport, W.1/W.2) — DONE, all shipped per `docs/log.md` 2026-06-03/04 (44 tools live). Doc's `[ ]` boxes are stale, superseded by `remaining3.md` + the log.
- `done/remaining.md` C1 (official FIFA seeding) — DONE via C1 bracket build (`docs/log.md` 2026-05-30). C2/A3 (F1 gather) — DONE in `f1/intel_tools.py:27-36,87,164,233,377`. A3 cold-burst — DONE/mitigated by gather + semaphore (Phase O). D Phase 5 release — DONE (PyPI 0.3.2). D Phase 6 OTel — SUPERSEDED (deliberately excluded). B1 squad seeds — accepted empty-but-valid terminators, parked. B2 RapidAPI — operator decision, no code. A2 WC scoping — SUPERSEDED by live-conditioning (`results_state` + derived standings + `_FINISHED_STATUSES`); fold a post-tournament smoke check into Phase 7 instead. A4 `live_check.py` gaps — dev-only harness, never CI; optional.
- `done/update.md` W0/W1/W2a/W3 (conditioning, derived_standings, elo_live) — DONE in tree. Value-bets live-Elo nudge — DONE (`docs/log.md` 2026-06-17, rev `00011-dcc`). W2b Cloud Run keys+redeploy — SUPERSEDED (Cloud Run deleted Task 9). `int()` parse hardening — STILL OPEN, covered by Phase 4b (not duplicated here).
- `done/review-phase1-cleanup.md` #1/#2/#3 (health test + registry leak) — DONE (current `tests/unit/test_health.py` uses a monkeypatch registry fixture + real `get_health_report()` quota test). #4 standings docstring — DONE (matches code). #5 squad backlink — DONE (no cricsheet ref in file). #6 partly STALE (CricSheet legitimately reintroduced offline-only by D3a; only the `:22` parenthetical still wrong → Phase 5b). #7/#8 (rules cricsheet rows) — DONE (no refs in `.claude/rules/`). #9 dead import — DONE (no `InvalidInputError` in `cricket/tools.py`). #10 dead imports — DONE. #14 remote/PR — DONE (origin + pushes exist). #15 ADR-0008 — DONE (file exists). #11/#12/#13 test-strengthening — OPTIONAL, do opportunistically inside Phase 1/2 gates, not blocking.
- `done/v2c-provider-keys-plan.md` — DONE/SHIPPED; its "push + publish 0.2.3" follow-up SUPERSEDED by 0.3.2.
- `done/fable_ultimate.md` D2 circuits + D3a venues — DONE in tree; D1 abandonment — accepted (frozen seed). Its "commit + canary" follow-up is SUPERSEDED by Phases 7/8 of this file.
- `done/fable_test.md` workstreams — analysis asks, SUPERSEDED by later shipped work.
- `docs/raw/2026-05-30-step9-test-matrix.md` write-list — DONE, all four 0-coverage tools covered per `docs/log.md` step9 entry + current tests.
- `grok_agent.md` (standing cursor instructions) — mission complete, **Next:** none. Nothing to schedule; leave the file as the closed hosting-mission record.
- `grok_index.md` Waves A–C — all `[x]` DONE (hosting closed 2026-09-02). The 2026-08-30 note's uncommitted Dockerfile/README items landed in later commits (`5cfa12f` et al).
- `grok_changes1.md` (public docs → live Cloud Run URL) — DONE, superseded by Task 8 Dell flip. `2.md` (0.3.2 + version bind + server.json CI check) — DONE in tree. `3.md` (Dockerfile frozen + lockfile gate) — DONE (uv 0.12.6 + `uv export --frozen`). `4.md` (pin `mcp<2`, crypto upgrades, pip-audit cron) — DONE. `5.md` (reserve/refund, odds sibling keys, cricket NOT_FOUND, HTTP wiring test) — DONE. `6.md` (GAPS/PROJECT/CLAUDE/AGENTS/cloud/SECURITY/wiki/log refresh) — DONE. `7.md` (commit+push+PyPI option) — DONE (`c2b5b7e`, PyPI 0.3.2; its 4 unchecked boxes at `:105-108` are stale tracking in a closed file — CI green, PyPI live, README Dell URL, `12.md` tracking all hold in reality). `8.md` (overlay index + brief + inventory) — DONE (written). `9.md` (`TRUST_CLOUDFLARE` → `CF-Connecting-IP`) — DONE. `10.md` (compose no-ports, `.env.example`, HEALTHCHECK) — DONE. `11.md` (Caddy + playbook + steel docs) — DONE. `12.md` Tasks 5–9 (clone, Caddy, hostname, flip, GCP teardown) — DONE 2026-08-30/09-02. `13.md` (stateless HTTP) — DONE. Per `grok_agent.md:31-38`: files 1–6, 9–11, 13 were already applied when written — do not re-implement, verify only.
- `muse.md` (verified 2026-09-05 audit briefing) — GOVERNING, not done: it is the correction source for Phases 1–6 of this file (see header). Local-only; Phase 6 gitignores it.
- `.codex/` (`config.toml`, `agents/*.toml`, `hooks.json`, `hooks/*.sh`) — tool configs (RapidAPI MCP remotes with `<KEY>` placeholder, agent briefs, bash guards). No plan content, nothing to schedule.
- `docs/superpowers/plans/2026-07-14-codex-changes-review-blockers.md` — self-marked **Completed 2026-07-14** (finding filed). `2026-07-14-codex-changes-hardening-correctness.md` (+ spec) — executed on `codex_changes` (GAPS items RESOLVED 2026-07-14). `2026-05-30-c1-official-bracket-seeding.md` (+ spec) — DONE (bracket ships). `2026-08-13-home-server-migration.md` — DONE (Dell live, Task 9 teardown).
- `done/codex_changes1–4.md` + `done/codex_suggestions.md` — archived planning docs ("no change implemented" headers predate execution; zero checkboxes in any of them); content landed via the 2026-07-14 codex pass. Leave untouched as history.
- Checkbox audit 2026-09-05 (unchecked `- [ ]` ≠ remaining work — each verified against tree artifacts): hardening-correctness plan 58 open/0 done BUT `request_limits.py` + ADR-0012 + `test_ratelimit_atomic.py` + `test_request_limits.py` all in tree → executed without ticking boxes. C1 plan 25 open/0 done BUT `wc2026_bracket.json` ships + log entry → executed. Home-server plan 44 open/0 done BUT Dell live + Task 9 teardown → executed. Review-blockers 0 open/31 done → executed AND ticked. Conclusion: nothing left to do in any grok/codex/superpowers file — the only live plan is this `order.md` checklist. Yes, we can move ahead: Phase 0 baseline → Phase 1.
- `docs/superpowers/plans/2026-08-13-home-server-migration.md` + codex plans/specs — DONE (Dell live, Task 9 teardown).
- `launch/01-launch-and-deploy.md` tag/publish v0.2.0 + publisher setup — SUPERSEDED/DONE (Trusted Publishing live, PyPI 0.3.2, registry remotes = Dell, Glama synced). Its `[ ]` README/listing boxes predate the shipped README refresh; remaining listing-copy work is local-only marketing, not scheduled. `launch/README.md:13-20` "June 5 / kicks June 11" timing — STALE (tournament over). `launch/10-market-and-positioning.md:83-97,108` fork decision — DONE as parked.
- `API-KEYS-AND-SETTINGS.md`, `dev.md` (non-dashboard parts), `sep.md`, `gcp.md`, `muse.md`, `grok_agent.md`, `website/website.md`, `website/CLAUDE.md` — no executable code tasks for this batch; their stale Cloud Run passages are covered by Phase 5c (where tracked) or left as local-only history.

## Appendix B — deferred, needs a decision first (DO NOT schedule without ADR/yes)

- B1. `cricket_find_value_bets` live-up: needs the reliability-curve validation phase first (`PROJECT.md:185-188`, `cricket/models/win_probability.py:20`, `cricket/intel_tools.py:613-630` intentionally returns `[]`). Gate, not a build task.
- B2. `matchups.json` batter-vs-bowler H2H: blocked on name reconciliation (Cricsheet initials vs `squads.json` full names, 25/194 exact-match). A hand-curated alias table conflicts with the no-hand-curated-player-data rule — needs an explicit decision before any build (`docs/log.md` D3a lines 444-449, `scripts/build_cricket_priors.py:17-23`).
- B3. `match_id` → Odds-API event resolver (`done/remaining.md:11-16`, deferred stretch since step8): team-substring filter stays until someone funds the fuzzy-match work. Low payoff, schedule only on request.
- B4. Fantasy roadmap (`launch/09-product-roadmap-fantasy-patterns.md:40-82`, `launch/08-data-sources-fantasy-platforms.md:66-90`, `launch/10-market-and-positioning.md:103-106`): football/F1 fantasy XIs, transfer optimizers, chip advisors, differentials, price predictors, F1 Fantasy adapter, real ownership feed. Needs scope decision (post-WC timing changes the value) + ADR per tool; each is at least one design + build + test task. NOT in Phases 1–8.
- B5. `v3.md` Parts A/B (multi-provider keys router, activation/metering V2.5): metric-gated post-revenue (`v3.md:91-93`); file is self-marked partially stale. NOT in Phases 1–8.
- B6. `BACKLOG.md` all items (Entity/Sportmonks/Sportradar/OddsMatrix, live F1 timing, OR-Tools, OTel, SQLite search, NHL/NBA, ML projections, SSE, i18n, per-user cache): ADR-gated by definition. NOT in Phases 1–8.
- B7. GAPS #10 Redis re-probe + any shared-Redis move: deferred until Redis exists (zero-spend). GAPS #13 `scripts/` generator tests: optional hardening, schedule only on request.

## Notes (append, do not rewrite history)

- 2026-09-05: file created on `audit-fixes`; Phases 1–8 unexecuted.
- 2026-09-05: full-markdown sweep folded in — Phases 4d/4e/5b/5e extended (A5, A6, ADR-0007:22, chains docstring, consistency checklist); Appendices A/B added so every scanned plan file has a verdict and an execution slot or a reason it has none. Still unexecuted.
- 2026-09-05: grok/codex itemization — every `grok_changesN.md`, `grok_agent.md`, `.codex/`, superpowers codex plans, `done/codex_*` individually verdict-recorded in Appendix A (all DONE/closed — do-not-reimplement). Checkbox audit: hardening 58/0, C1 25/0, home-server 44/0 open-but-executed (artifacts in tree); review-blockers 0/31 ticked; `grok_changes7` 4 stale boxes satisfied in reality. `muse.md` adopted as governing correction source: 1b widened to F1 gather + `Exception`-only, 1e de-overstated, 2b selective, 3a extractor scope, 3c skill-direction, 3d/3e + points + match_resolver marked optional, 4b `_is_finished`, 5a de-scoped (no SECURITY rewrite, test.yml comment, real collect count, GAPS pin wording), 5c default-skip for gitignored docs, 5d de-scoped (no simulate_group delete), Phase 6 + `.gitignore` cover `muse.md` itself. Still unexecuted.

- 2026-09-11: reconciled on **`bot`** tip `971b16f` (suite **814**) vs grokbot audits. ACTIVE BRANCH retargeted from `audit-fixes` → `bot`. `order.md` copied into `.worktrees/bot` (`muse.md` not required). Local commit of `order.md` only — **no push**.
- **Ticked:** Phase 0 baseline 814; 1a cricket NotFoundError (`13e2104`); 1c pit None/unknown (`13e2104`); 1d Dream11 CBC InvalidInputError (`13e2104`); 2a PARTIAL api_football + FD.org empty (`77bef8f`/`b395f15`); 4b form_trends + goal coerce (`13e2104` + R4 xG); 5d value_bet skip <=0 (`13e2104`).
- **Weather/pit extras:** R1 weather rainfall DONE `ad8cefa`; R5 pit non-numeric rainfall DONE `9da5ffa` — related to pit/weather; see Notes (not separate phase bullets in original order).
- **Docs:** GAPS/value-bet/weather docs DONE `971b16f`.
- **PARTIAL/CONFLICT left unchecked:** 1b gather Exception→envelope — later R7 changed race-pace/player-matchup to RE-RAISE unknowns (`971b16f`); do not force wrong tick.
- **Left unchecked / DEFERRED:** 2b OpenF1 selective (R6 SKIPPED); openfootball/static_seed/TeamStats if unfinished; 3c skill dream11; Phase 7 push-to-main; Phase 8 deploy.
- **Next first unchecked in order:** 1b (PARTIAL/CONFLICT — resolve vs R7 before forcing), else 1e sim-model errors.
- 2026-09-11 (bot work session): **1b SKIPPED per instruction — R7 stands** (race-pace/player-matchup re-raise unknowns `0534834`; do not force envelope tick). **1e DONE** — `football_simulate_group`/`football_simulate_bracket`/`football_knockout_path` catch `(ValueError, KeyError)` → `INVALID_INPUT` (`intel_tools.py`); 4 tool-level tests in `tests/tools/test_football_tools.py` (malformed draw ×3 + KeyError combo ×1). **Phase 2 remainder DONE** — AF TeamStats empty-guard; FD TeamStats always-`NotFoundError` (wrong endpoint/ID space, walks off chain); openfootball empty-`matches` raise; static_seed groups/fixtures missing-file raise (squad terminator untouched); derived_standings via lazy `football_fixtures_chain.fetch()` + health registration. New adapter tests: AF TeamStats, FD TeamStats, openfootball empty, static_seed missing ×2, derived chain-routing. Evidence: targeted gate `tests/tools + pit + dream11 + group_sim + bracket_sim` **338 passed**; adapter+chain gate **39 passed**; full `uv run pytest` **824 passed** (baseline 814 + 10 new); `ruff check` clean. 2b (OpenF1/jolpica, R6 SKIPPED), 1b, Phase 3–6, Phase 7 push, Phase 8 deploy remain open.

