# Operation log

Append-only. Grep with `grep "^## \[" docs/log.md`.

Operations: `ingest` · `decision` · `lint` · `release` · `tool-added` · `adapter-added` · `finding-filed` · `cache-cleared` · `phase-complete` · `ci` · `fix`.

## [2026-06-04] tool-added | cross_sport_build_accumulator

`normalise_pick` helper added to `core/parlay.py` (sport-prefixed `match_id` for cross-sport dedup). `cross_sport_build_accumulator` tool in `server_tools/cross_sport.py`; concurrent football + cricket value-bet fetch via `asyncio.gather`; one sport failure non-fatal. 4 unit tests + 5 tool-layer tests. Wiki: `docs/wiki/tools/cross-sport-accumulator.md`.

## [2026-06-04] tool-added | f1_race_pace_compare

`compare_race_pace` pure model in `src/sportiq/f1/models/race_pace.py` (per-compound intercept comparison via `fit_degradation`). `f1_race_pace_compare` tool in `intel_tools.py`; 4-way concurrent fetch (laps + stints for both drivers); stints best-effort. 5 unit tests + 4 tool-layer tests. Wiki: `docs/wiki/tools/f1-race-pace-compare.md` + `docs/wiki/models/race-pace.md`.

## [2026-06-04] tool-added | cricket_player_matchup

`compute_matchup` pure model in `src/sportiq/cricket/models/player_matchup.py` (batter_vs_bowler / batter_vs_batter / bowler_vs_bowler role classification; batting_avg, bowling_avg, strike_rate edge detection; None-safe). `cricket_player_matchup` tool in `intel_tools.py`; concurrent `asyncio.gather` player stats fetch; `meta.estimated: true`. 14 unit tests + 9 tool-layer tests. Wiki: `docs/wiki/tools/cricket-player-matchup.md` + `docs/wiki/models/player-matchup.md`.

## [2026-06-03] tool-added | f1_qualifying_analysis

`best_lap_per_driver`, `gap_to_pole`, `grid_projection` pure functions in `src/sportiq/f1/models/quali_analysis.py`. `f1_qualifying_analysis` tool in `intel_tools.py`; routes through `f1_laps_chain` + `f1_drivers_chain` for name enrichment; returns projected grid with gap-to-pole seconds. 8 unit tests + 4 tool-layer tests. Wiki: `docs/wiki/tools/f1-qualifying-analysis.md` + `docs/wiki/models/quali-analysis.md`.

## [2026-06-03] tool-added | football_build_accumulator
`build_accumulator` pure model in `src/sportiq/core/parlay.py` (edge filter, dedup by match, combined odds/prob/edge under independence, risk flag). `football_build_accumulator` tool added to `intel_tools.py`; calls `football_find_value_bets` directly; `meta.source: derived`, `meta.estimated: true`. 7 unit tests + 6 tool-layer tests (466 total). Wiki: `docs/wiki/tools/football-build-accumulator.md` + `docs/wiki/models/parlay-builder.md`.

## [2026-06-03] tool-added | football_form_trends
`compute_form_trends` pure model in `src/sportiq/football/models/form_trends.py`; `football_form_trends` tool registered in `intel_tools.py`. Routes through `football_fixtures_chain`. Off-season graceful (empty envelope + note). 7 unit tests + 5 tool-layer tests. Wiki: `docs/wiki/tools/football-form-trends.md`.

## [2026-06-03] tool-added | cricket_head_to_head
Feature 2 complete. **2.1:** `src/sportiq/cricket/models/head_to_head.py` — `summarise_h2h()` pure function: scores each squad by `player_form_index`, counts positional form edges, derives `h2h_win_rate_*` from edge ratio. **2.2:** `cricket_head_to_head` tool added to `intel_tools.py`; fetches squads + player stats concurrently (semaphore=5); folds H2H rate into `win_prob()`; `meta.estimated: true`. `player_form_index(raw_stats)` helper added to `form_index.py`. **Tests:** 16 new tests (8 unit + 8 tool). **Wiki:** `docs/wiki/tools/cricket-head-to-head.md`.

## [2026-06-03] tool-added | cricket_find_value_bets + win probability model
Feature 1C complete. **1C.0:** `src/sportiq/core/value_bet.py` — canonical home for `implied_prob`, `devig`, `find_value`, `_OUTCOME_TO_MODEL`; `football/models/value_bet.py` now re-exports from core (no behaviour change). **1C.1:** `src/sportiq/cricket/models/win_probability.py` — heuristic T20 win probability (form 50%, H2H 30%, venue tilt 20%); pure function, no I/O, defaults to 50/50 on missing signals. **1C.2:** `cricket_find_value_bets` tool added to `intel_tools.py`; reuses `odds_chain`; `meta.estimated: true` always set. **Tests:** 10 new tests (7 unit + 3 tool → 404 total). **Wiki:** `docs/wiki/tools/cricket-find-value-bets.md` + `docs/wiki/models/cricket-win-probability.md`.

## [2026-06-03] perf | Phase O — concurrency caps, load harness, TTL verification, duration_ms in staleness_meta
**O.1:** `_F1_LAP_SEMAPHORE = asyncio.Semaphore(5)` + `_fetch_driver_laps()` helper in `f1/intel_tools.py`; `f1_head_to_head_pace` and `f1_undercut_window` now route per-driver lap fetches through the semaphore. **O.2:** `_SERVER_SEMAPHORE = asyncio.Semaphore(20)` in `server.py` as infra guard against malformed client bursts. **O.3:** `tests/unit/test_o3_cache_ttls.py` — 12 TTL assertions across cricket/F1/football chains; discovered `f1_laps_chain` and `f1_stints_chain` had stale `fresh_ttl=3600/stale_ttl=86400` — corrected to `10/60` per caching-policy.md. **O.4:** `scripts/load_check.py` — 20-concurrent stubbed tool calls; wall time 12ms, PASS. **O.5:** `staleness_meta()` now includes `duration_ms: sum(...)` so all intel tools auto-surface chain timing. **Tests:** 394 pass (382 → 394). **Ruff:** clean.

## [2026-06-03] decision | ADR-0010 PyPI Trusted Publishing (OIDC) — manual PyPI setup documented
**S.9a closeout.** Supply-chain risk mitigation: long-lived PyPI API tokens replaced with short-lived OIDC identity proofs from GitHub Actions. **Code side ready** — the release workflow uses `pypa/gh-action-pypi-publish` (OIDC mode, no explicit token). **Manual one-time setup required:** operator adds a GitHub Actions publisher in PyPI's web UI (https://pypi.org/manage/project/sportiq-mcp/settings/publishing/) — proof recorded in `ADR-0010`. **Build artifact verification:** `pyproject.toml` gained `[tool.hatch.build.targets.sdist]` with excludes (`.env`, `.env.*`, `docs/raw/`, `docs/graphify/`, `tests/fixtures/`, `scripts/`, `*.local.md`, `step*.md`); new `scripts/check_release_build.py` validates both wheel + sdist against these patterns at build time (exit 0 = no leaks). **CI:** new `.github/workflows/security.yml` job `release-build-check` runs the script on push/PR. **Tests:** 382 pass, ruff clean, script verified locally (0 violations). **Wiki:** `docs/wiki/decisions/0010-trusted-publishing.md` + indexed in `docs/index.md`. Step10 Phase S.9a DONE.

## [2026-06-03] ci | S.7a — pip-audit + bandit + gitleaks gates added
**Scope:** CI dependency scanning gates + hardcoded `/tmp` path hardening. **New:** `.github/workflows/security.yml` with three jobs: `pip-audit --strict` (CVE scanning), `bandit -r src -ll` (static security analysis), `gitleaks` (committed-secret detection). **Added to dev:** `pip-audit>=2.7.0`, `bandit>=1.8.0`. **Fixed:** `src/sportiq/f1/adapters/fastf1_local.py` — replaced hardcoded `/tmp/fastf1_cache` paths with `tempfile.gettempdir()` (B108 MEDIUM findings). **Audit result:** 1 transitive CVE flagged (`diskcache 5.6.3 CVE-2025-69872` pickle RCE); mitigated by local-only use (cache dir `~/.cache/sportiq/` owned by user). **All gates pass:** Bandit 0 MEDIUM+ on src, ruff clean, **377 tests**. Step10 Phase S.7a DONE.

## [2026-06-03] finding | S.4 untrusted-upstream posture — SECURITY.md, payload caps, scraper HTML assertion

## [2026-06-03] finding-filed | error-envelope-secret-leak (+ ADR-0009)
S.1d closeout for the secret-redaction work. Filed `docs/wiki/findings/error-envelope-secret-leak.md` — the query-param API key (CricAPI, TheOdds ×2) leaked via the *error* envelope's `sources_tried` (httpx exception URL captured in `fallback.py` attempts/log); distinct from the success-body echo in [[cricapi-envelope-leak]] (cross-linked both ways). Added `docs/wiki/decisions/0009-secret-redaction.md` (ADR-0009) recording the choke-point decision and the rejected "scrub inside get_json" alternative (would break tenacity retry typing). Indexed both under Findings + Decisions in `docs/index.md`. Fix itself shipped earlier (`4ddd8f6`); remaining S.5/S.6 noted in step10 Phase S.

## [2026-06-03] decision | stop committing step planning docs
Per user: don't commit the `step*.md` planning docs going forward. Dropped the unpushed `step10.md` rebaseline commit (`81ae867`) via `git rebase --onto` (safety branch `backup-before-step10-drop`); the rebaselined step10.md is preserved on disk as an uncommitted working copy. Added `step*.md` to `.gitignore` — forward-looking only: `step5–9.md` are already tracked and **stay on origin untouched** (gitignore doesn't untrack them); this just stops brand-new step files (and the local step10.md copy) from being added. The S.1 redaction fix + gitignore-narrow commits are unaffected.

## [2026-06-03] fix | .gitignore — narrow the over-broad `*secret*` rule
The bare `*secret*` (line 37) matched ANY path containing "secret" and silently un-staged source/tests — it ate `tests/chains/test_chain_redacts_secrets.py` during step10 S.1 (renamed to `test_chain_key_redaction.py` to work around it). Replaced with extension/name-scoped patterns (`*.secret`, `*.secrets`, `secrets.{json,yaml,yml,toml,env}`, `client_secret*.json`, `.env.secret`) so real secret artifacts stay ignored while `.py`/`.md` source with "secret" in the name is tracked. Verified with `git check-ignore` both ways. The `*_key_redaction` test keeps its name (no need to rename back). `.env`, `*.key`, `*KEYS*.md`, `API-KEYS-AND-SETTINGS.md` still cover the primary secret files.

## [2026-06-03] fix | step10 S.1 — redact API keys from the error envelope + logs
🔴 secret-leak closed. `core/http.py:get_json()` raises `httpx.HTTPStatusError` whose string embeds the request URL; CricAPI + The Odds API (cricket + football) pass the key as a `?apikey=`/`apiKey=` query param, so `str(e)` flowed into `core/fallback.py` `attempts` → the error envelope's `sources_tried` (and the failure log), disclosing the key to the MCP client/LLM. New `src/sportiq/core/redact.py` `scrub()` — a single choke point that redacts (1) known-secret query params (positional match so OpenF1's `session_key` is left intact), (2) Authorization / x-rapidapi-key headers, (3) the literal credential values from `settings`. Applied at both `fallback.py` capture sites (attempts `error` + failure log). Tests: `tests/unit/test_redact.py` (8) + `tests/chains/test_chain_key_redaction.py` (2, real `HTTPStatusError` through the chain → key absent from attempts + `sources_tried`; filename avoids the `*secret*` gitignore rule). Suite 318 → 328, coverage 87%, ruff clean. Remaining S.1 follow-up: ADR-0009 + `/project:file-finding` write-up (S.1d), and S.5 logging-processor / S.6 redirect hardening (tracked in step10 Phase S).

## [2026-06-03] fix | step9 review — live-call leak, coverage foot-gun, stray dep-group
Review of the step9 diffs (`953e9f5..7bee084`) surfaced three issues, all fixed here. (1) 🟠 `tests/tools/test_health_tool.py` called `get_health_report()` unmocked, which awaits `healthcheck()` on every registered adapter; the first `cricapi` adapter (`CricAPILiveMatchesAdapter`) makes a live `/currentMatches` call when `CRICAPI_KEY` is set — and the local `.env` has one, so every `uv run pytest` was hitting CricAPI live (quota burn + breaks the no-live-HTTP rule; CI hid it by having no key). Fixed by stubbing `health._registered_adapters` with inert fakes in the test, **plus** an autouse `no_live_credentials` fixture in `tests/conftest.py` that blanks all credentials + scraper toggles so no test can ever leak a keyed call. (2) 🟠 `--cov-fail-under=84` lived in `addopts`, failing any subset/TDD run even when all selected tests passed; moved the gate to the CI command only (`addopts` back to `-q --strict-markers`). (3) 🟡 removed the stray PEP 735 `[dependency-groups] dev` (pytest-cov only) duplicating `[project.optional-dependencies] dev`; `uv lock` regenerated. Suite **316 → 318**, coverage 87%, ruff clean.

## [2026-05-30] phase-complete | step9 — exhaustive test matrix + coverage gate
**Scope:** Part 0 (step10 staleness banner) + Part 1 (matrix doc + C1 bracket regression + tool/chain gaps + coverage gate). No new tools. **291 → 316 tests, coverage 88%, ratchet floor 84%.** Key additions: (1) `docs/raw/2026-05-30-step9-test-matrix.md` — 36-tool coverage matrix + prioritized write-list. (2) `tests/unit/test_bracket_data.py` — C1 `_build_r32` runtime property test: 32 distinct teams, no intra-group R32 pairing. (3) `tests/tools/test_f1_tools.py` +16 — `f1_get_drivers` and `f1_get_standings` (0→covered), missing INVALID_INPUT/ALL_SOURCES_FAILED paths, meta-field assertions. (4) `tests/tools/test_football_tools.py` +10 — `football_get_top_scorers` (0→covered), missing success/error paths for fixtures/standings/groups/match_stats, meta-field assertions. (5) `tests/tools/test_health_tool.py` new — `sportiq_health` (0→covered): shape, data fields, meta version. (6) `pyproject.toml` + `test.yml` — `pytest-cov` in dev deps, `--cov-fail-under=84` ratchet wired into CI, `fastf1_local.py` + `server.py` excluded (optional/bootstrap). Live check (F1 keyless): OpenF1 + Jolpica healthy, 11/11 F1 tools pass live; keyed-source fixtures hand-crafted but validated in step8. Deferred: step10 rebaseline; remaining.md A1/A2/A3/A4 (tracked, unchanged).

## [2026-05-30] decision | step8 Part 3 — squad gap-fills (cricket + football seeds)
**3.1** `cricket/data/squads.json`: added 5 international squads (SA, PAK, SL, WI, BAN), 15 players each, matching
the existing `{name, role, credits}` shape — `cricket_get_squad` + Dream11 now work offline for them (the new
`series_id` guard from Part 1 makes the chain fall to the seed cleanly). **3.2** football squad terminator was
empty-but-valid for everyone; added `football/data/football_squads.json` with 8 marquee WC rosters (ARG, BRA,
FRA, ENG, ESP, GER, POR, NED), 15 players each `{name, position}`, wired via `load_football_squads()`.
Unseeded teams still return the empty-but-valid shape (NOT_FOUND invariant intact). **3.3** (match_id→Odds-API
event resolver) deferred — explicit "only if time" stretch. 2 new tests (287 total), ruff clean.

## [2026-05-30] tool-added | football_find_value_bets (step8 Part 2)
New INTEL flagship: de-vigs live bookmaker 1X2 odds and compares to the server's own match-outcome
probabilities (the same Elo→Poisson path `football_match_predictor` uses) to surface +EV "value" bets with
edge %. Pure reuse — no new data source. New model `football/models/value_bet.py` (`implied_prob`, `devig`
multiplicative, `find_value`); tool `football_find_value_bets(team=None, min_edge=0.05)` reuses
`football_odds_chain` + `football_groups_chain`, maps odds team-names→rating codes via the draw's `teams`
block (events with an unrated side are skipped), runs `find_value` per bookmaker, sorts by edge desc, and
propagates **odds** staleness to `meta`. Validates `min_edge ∈ [0,1]` → INVALID_INPUT. **36 tools.** Live
smoke: 38/72 events analysed, 367 picks. 12 new tests (285 total: 8 value-bet unit + 4 tool), ruff clean.
Wiki: [[value-bet]] + [[football-find-value-bets]].

## [2026-05-30] finding-filed | step8 Part 1 — live testing pass against real upstreams
Built `scripts/live_check.py` (standalone, never in CI) and ran it with live keys. **35/35 tools enumerate**
in the MCP schema (Pass C), all typed + described. **F1 (keyless):** 11/11 healthy; `f1_predict_pit_strategy`
inferred Bahrain `total_laps=57` (validates step7 inference + step8 `lap_number>0` guard); undercut/h2h hit a
benign transient OpenF1 cold-burst that self-recovers. **Football:** off-season empties for
fixtures/standings/scorers (WC 2026 not started — expected), squad empty-but-valid, all 5 sim flagships OK,
odds returns 72 live events. **Cricket — two real bugs found + fixed:** 🔴 `CricAPIScorecard/PointsTable/PlayerInfo`
adapters returned the raw CricAPI envelope, **leaking the request `apikey`** into tool output and treating
`status:"failure"` bodies as empty successes; 🟠 `CricAPISquadAdapter` with `series_id=None` "succeeded" empty
and cached it, **shadowing the 11-player static seed**. Fix: `_unwrap()` strips the envelope + raises
`NotFoundError` on non-success; squad raises without a `series_id` so the chain falls to `static_seed`;
scorecard/points-table tools now emit `NOT_FOUND`. Filed [[cricapi-envelope-leak]] +
`docs/raw/2026-05-30-step8-live-findings.md`. 4 new tests (273 total), ruff clean. scorecard/points-table now
return honest `ALL_SOURCES_FAILED` (CricAPI free tier excludes those endpoints) — not a bug.

## [2026-05-30] decision | step8 Part 0 — derisk before live testing
**0.1** `core/http.get_json` no longer retries 4xx: a custom `_should_retry` predicate retries only `httpx.TransportError` and `HTTPStatusError` with `status_code >= 500`. A bad-auth/quota (401/403/404/429) response now costs **one** upstream call, not three — aligns code to the docstring contract before the quota-spending live pass. **0.2a** `f1_predict_pit_strategy` `total_laps` inference filters `lap_number > 0` (guards a stray 0/None lap from collapsing the race length). **0.2b** two squad-terminator tests (`cricket`/`football_get_squad` with key unset) lock the NOT_FOUND invariant: unknown team → no raise, `meta.source == static_seed`. **Config blocker found + fixed:** the committed `.env.example` shipped inline `# comments` trailing each `VAR=value`; the built-in pydantic-settings dotenv parser (no python-dotenv dep) reads the comment as the value, and a blank `SPORTIQ_ENABLE_NDTV=` is an empty string that fails `bool` parsing → server/tests wouldn't boot. Fixed: comments moved to own lines in `.env.example`, plus a `field_validator` coercing blank scraper toggles → `False`. 7 new tests (269 total), ruff clean.

## [2026-05-29] phase-complete | step7 — Phase 4.5 review fixes + step5 #6/#7/#8 + RapidAPI MCP wiring
Three commits. **A1** odds budget honesty: both TheOddsAPI adapters use `regions=uk` (1 credit/request ≈ 480/month, under the 500/month cap; `uk,eu` was ~960/month). **A2** football odds capture the 1X2 Draw price → `{name, home, draw, away}`; cricket (T20) stays `{name, home, away}`. **#6** `FallbackChain` re-raises `NotFoundError` when every adapter that ran reported the entity missing (none skipped/failed otherwise), making the tool-level `except NotFoundError` live — `cricket_get_pitch_report(venue=<unknown>)` now returns `NOT_FOUND`. **#7** `f1_predict_pit_strategy` `total_laps` → `int|None`; when omitted, inferred from max observed `lap_number` (Monaco 78 / Spa 44), else 57; resolved value echoed in `meta.total_laps`. **#8** `ratelimit` split into `has_budget` (peek) + `consume`; chain peeks before fetch and consumes only after success, so failed/missing-key calls burn no quota. **Part C** wired 3 RapidAPI Hub `mcp-remote` servers (Sportspage Feeds, Football Prediction, Live Sports Odds) into `.mcp.json` with a committed `<RAPIDAPI_KEY>` placeholder (operator fills locally). 4 new tests (262 total), ruff clean.

## [2026-05-29] phase-complete | Phase 4.5 — Odds layer (The Odds API)
Added live bookmaker h2h odds across cricket + football. 2 adapters (`cricket/adapters/theodds.py` sport key `cricket_ipl`, `football/adapters/theodds.py` sport key `soccer_fifa_world_cup`) — shared `core.http` client, per-sport normaliser duplicated by design, both raise `MissingCredentialsError` without `THEODDS_KEY`. 1 shared `theodds` budget (`per_day=16` slice of the 500/month free tier). 2 chains (`odds_chain`, `football_odds_chain`) — 5min fresh / 24h stale, sport-wide cache key. 2 tools (`cricket_get_live_odds(team=None)`, `football_get_odds(team=None)`) = **35 tools**; optional team-name substring filter applied at the tool layer (match_id→event mapping deferred — The Odds API uses opaque event ids). 12 new tests (respx adapter + stubbed-chain tool tests), ruff clean. Cross-cutting: `THEODDS_KEY` in config + .env.example, api-budgets row, caching-policy odds row, 5 wiki pages (data-source + 2 chains + 2 tools), index entries.

## [2026-05-29] finding-filed | step6 review fixes — A1, A2, A4 + remote rename
Fixed 3 step6 review findings. **A1**: `APIFootballSquadAdapter.fetch` now raises `NotFoundError` on an empty `response` (a country code where api_football wants a numeric id) so `football_squad_chain` walks past to the static seed instead of stopping on an empty success. **A2**: sharpened `football_get_match_stats` docstring — network-only enrichment, numeric id, no offline static fallback (clean ALL_SOURCES_FAILED without a key). **A4**: lowered `_MAX_ITERATIONS` 50000→20000 in `football/intel_tools.py` (worst-case bracket latency ~4s) and updated the three "100..50000" docstrings. 4 new tests (246 total), ruff clean. Housekeeping: GitHub repo renamed sportiq-mcp→SportIQ-MCP; corrected `origin` URL. Deferred (optional): A3 (asyncio.gather in F1 INTEL), A5 (groups-chain 1yr TTL), A6 (wiki link nits).

## [2026-05-29] phase-complete | Phase 4 — Football RAW + INTEL flagship #3
Built the whole `src/sportiq/football/` module. 6 RAW tools (groups, fixtures, standings, squad, match_stats, top_scorers) + 5 INTEL (xg_model, match_predictor, simulate_group, simulate_bracket flagship, knockout_path) = 11 tools, 33 total. 4 models (poisson_xg Poisson scoreline engine, elo, group_sim round-robin MC, bracket_sim full-tournament MC). 6 chains (fixtures: api_football→football_data_org→static; standings; groups static terminator w/ draw+ratings; team_stats; squad; scorers). 3 adapter sources (api_football keyed, football_data_org token-optional, static_seed). Data: wc2026.json (48 teams, 12 groups A-L, top-2 + 8 best-thirds → R32) + elo_seed.json. **Encoded the 2026 48-team format, not 2022.** Flagship verified: reach_r32 mass==32, win mass==1, monotone round probs, ±2% convergence at ~10k iters, group p_advance==2. config.footballdata_key added (optional). server registers football tools. 52 new tests (242 total), ruff clean. 24 wiki pages + ADR-0008 + monte-carlo-bracket skill + README/index. Bracket seeding is strength-based (not the official FIFA third-place table) — documented follow-up in ADR-0008.

## [2026-05-29] phase-complete | Phase 3.1 — F1 corrections + differential recalibration
Landed audit findings #1, #2, #3, #5 (and #4). #1: added `annotate_laps_with_stints` (tyre_deg.py) merging OpenF1 `/stints` compound + `tyre_life` onto `/laps`; wired into `f1_tyre_degradation` and `f1_predict_pit_strategy`, so the flagship runs on telemetry not TyreSpec constants. Stint/weather enrichment is best-effort — laps are required but an enrichment-source outage degrades quality (`meta.stint_enrichment`/`weather_enrichment` flags) instead of failing the call. Re-recorded `laps_session9877.json` (real shape — no compound/tyre_life) + `stints_session9877.json`. #2: `f1_sessions_chain` is now OpenF1-only (Jolpica fallback raised TypeError on every call). #3: rescoped `f1_get_race_results(year, round)` onto a new `f1_results_chain` (Jolpica results.json) returning real `data.results`, not the drivers stub. #5: added `staleness_meta()` helper; all 5 F1 INTEL + cricket build_dream11/captain/differential now surface `is_stale`/`data_age_seconds`/`fallback_used`. #4: recalibrated differential ownership proxy from `credits*7` (always ≥49% → empty) to a linear 7.0→5% / 11.0→90% curve. 189 tests (+6), ruff clean. Wiki + index updated.

## [2026-05-28] decision | step5 — Phase 0–3 audit + Phase 4 (Football) plan
Audited Phases 0–3; filed 8 bugs in step5.md. 1 HIGH: F1 tyre-deg flagship is inert on real OpenF1 data — `/laps` carries no compound/tyre_life (those are on `/stints`), and the laps fixture bakes a shape OpenF1 never returns, so `fit_degradation`/`pit_strategy` fall back to TyreSpec constants in production. 3 MED (sessions-chain fallback TypeErrors; `f1_get_race_results` returns drivers not results; `differential_picks` always empty under default threshold; INTEL tools drop is_stale). Wrote step5.md = audit + Phase 4 Football flagship #3 plan + recommended Phase 3.1 fix-first pass. No source changes this op.

## [2026-05-28] phase-complete | Phase 3 — F1 RAW + INTEL flagship #2
6 F1 RAW + 5 F1 INTEL tools (including f1_predict_pit_strategy flagship). 3 models (tyre_deg, undercut, pit_strategy). 6 chains (sessions, laps, stints, weather, standings, drivers). 3 adapter sources (openf1, jolpica, fastf1_local lazy-imported). 22 total tools. Tyre constants in data/tyres.py; points in data/points.py. Phase 2.1 cleanup also landed (match_id resolver, Dream11 skill, PuLP migration, doc polish).

## [2026-05-28] phase-complete | Phase 2 — Cricket INTEL flagship #1
5 INTEL tools (cricket_build_dream11_team, cricket_captain_recommendation, cricket_differential_picks, cricket_player_form_index, cricket_get_pitch_report). 5 new models (T20Scoring data + dream11_solver PuLP ILP via COIN_CMD/system cbc, captain_score projection, form_index 0-100, pitch_report). 2 new chains (player_stats: cricapi→rapidapi; pitch_data: static_venue terminator). 2 new adapter classes (CricAPIPlayerInfoAdapter, RapidAPICricbuzzPlayerStatsAdapter, plus CricAPIPlayerSearchAdapter reserved). Squad chain shape normaliser unified cricapi vs static_seed output. squads.json expanded with 4 internationals (IND, AUS, ENG, NZ). venues.json seeded with 14 IPL venues. 118 tests (58 new). Ruff clean. macOS arm64: requires `brew install cbc`.

## [2026-05-28] decision | API stack review — odds layer added as Phase 4.5
Validated current stack (CricAPI, OpenF1, API-Football + football-data.org) against production-grade alternatives. No changes to existing adapter choices. Added Phase 4.5 to plan.md: The Odds API (free, 500 req/month) for cricket_get_live_odds + football_get_odds. Enterprise upgrade paths (Entity Sport, Sportmonks, Sportradar, OddsMatrix) filed in BACKLOG.md under "API upgrade paths".

## [2026-05-27] cleanup | Phase 1 alignment pass
Fixed A1 (env aliases), A2 (scorecard chain), A3 (dropped player_stats), B1 (health dedup), B2 (rate-limit wired), B3 (register_cricket_tools), B4 (rule update), C1 (static-seed wiki), C2 (cricsheet URL/drop), C3 (fixtures init).

## [2026-05-26] phase-complete | Phase 1 — Cricket RAW + chains
5 tools (live_matches, scorecard, points_table, schedule, squad), 5 chains, 6 adapters (cricapi, cricsheet, ndtv_sports_scraper, cricbuzz_scraper, rapidapi_cricbuzz, static_seed). MissingCredentialsError added. Opt-in scraper posture enforced. static_seed pulled forward as squad terminator. ADR-0007 filed. 54 tests (45 new).

## [2026-05-26] phase-complete | Phase 0 — spine
Scaffolded the resilience primitives (`FallbackChain`, cache w/ Redis→diskcache auto-fallback, error envelope, rate limiter, structlog), FastMCP `server.main()` entry point, `sportiq_health` tool, and the full `.claude/` workspace (7 rules, 8 commands, 1 skill, 3 agents, 2 hooks). 6 ADRs filed. Tests cover FallbackChain ordering, cache backend selection, and stale-serve behavior.

## [2026-05-30] tool-added | C1: official FIFA bracket seeding

`football_simulate_bracket` now seeds the knockout from the official FIFA 2026 structure
(R32 template + 495-row Annex C best-thirds allocation + fixed R16→Final tree) instead of a
global strength reseed. Data generated by `scripts/build_wc2026_bracket.py` from
`docs/raw/fifa_data/` into `wc2026_bracket.json`. Draw/ratings unchanged (already equal the
provided data). All invariants preserved; suite 287→291.

## [2026-06-05] fix | outputSchema null-validation break (all 44 tools)
Root cause: `Envelope` TypedDict keys typed `dict[str, Any]` produced an
`outputSchema` of `{type: object}` per key, but FastMCP fills absent keys with
`null` in `structuredContent` (e.g. `error: null` on success). The mcp 1.27.1
lowlevel server validates output against `outputSchema` before sending, so every
tool failed with "None is not of type 'object'" (Inspector + any strict client).
Only `ping` (no schema) worked. Fix: typed the three keys `dict[str, Any] | None`
→ schema becomes `anyOf: [object, null]`. Added `tests/tools/test_output_schema_validation.py`
(88 RED → GREEN) validating both success/error envelope shapes against every tool's
outputSchema — the existing suite called tool fns directly and never hit this path.
Suite 508→607 passing.

## [2026-06-05] release | launch prep — README refresh, release workflow, MCP prompts
launch.md Tasks 1–3 (Task 4 monetization deferred by user). (1) README: fixed stale
"33 tools / Phase 4" → "44 tools / Phase 10", added the 11 steps-5–10 tools to the
RAW/INTEL tables, new Cross-sport + Diagnostics sections, CI/PyPI/tools badges, and
env-var-bearing Claude Desktop config. (2) Added `.github/workflows/release.yml` —
tag-triggered OIDC Trusted Publishing (ADR-0010); runs `scripts/check_release_build.py`
(builds + validates no sensitive paths) then `pypa/gh-action-pypi-publish`. One-time PyPI
publisher setup still pending. (3) Added `src/sportiq/core/prompts.py` (`register_prompts`,
5 prompts mirroring instructions.md recipes) wired into `server.py`, plus
`tests/tools/test_prompts.py`. Verified: 44 tools, 5 prompts, 1 resource load; suite 607→613;
ruff clean; build gate clean.

## [2026-06-05] feat | prompts 5→10 + release/packaging hardening
Follow-up audit (3 Explore agents). (1) Prompts: added 5 to round out 1:1 coverage of
the 10 instructions.md recipes — `cricket_captain_pick`, `predict_match`,
`build_accumulator`, `server_health`, `wc_group_situation` (verified target signatures).
Added `Args:` docstrings to all parameterized prompts and a `_clean()` helper that strips
string args and raises on blanks (prompt content is natural language, no escaping needed).
(2) Defense-in-depth: added `launch.md`/`new.md`/`remaining*`/`mcp-builder/` to both the
sdist `exclude` (pyproject) and `SENSITIVE_PATTERNS` (check_release_build.py) — those files
are untracked so they don't ship today, but the gate now fails if they're ever committed.
(3) release.yml hardened: concurrency guard (no cancel-in-progress), Python 3.12 pin,
`environment: pypi` on the publish job, and a `uv run pytest` quality gate before build/publish.
(4) Aligned GitHub URL case `sportiq-mcp`→`SportIQ-MCP` (pyproject urls + README clone/badge)
to match the actual remote; PyPI dist name unchanged. Two audit claims downgraded after
verification: CI badge was never broken (slugs case-insensitive) and working docs weren't
leaking. Verified: 44 tools, 10 prompts; suite 613→619; ruff clean; build gate clean.

## [2026-06-05] plan | go-to-market doc set (launch/) split out of marketing.md
Decomposed the `marketing.md` brain-dump into 8 focused, local-only strategy files under
`launch/` (README index + 01 launch/deploy, 02 monetization/pricing, 03 marketing playbook,
04 post drafts, 05 targeting list, 06 universal AI compatibility, 07 naming decision).
Locked decisions: keep `sportiq-mcp` name (Scenario A rename recipe preserved); monetize via
freemium (free RAW tools / paid INTEL behind `SPORTIQ_PRO_KEY`) using Polar (MoR on Stripe)
with **native license keys = zero hosting for V1** — Cloudflare Worker is optional V2. Grounded
facts via web: Polar free tier is 5%+$0.50 (fixed-fee gotcha → favor annual/lifetime), Polar
has native License Keys, and the official MCP Registry (Anthropic/GitHub/MS-backed, PulseMCP
auto-syncs) is now the #1 listing target. Flagged: `SUBSCRIPTION_REQUIRED` is NOT in the
exhaustive error-code table — the gate is a real Phase-2 code change. Time-sensitive: launch
into the WC 2026 window (kickoff ~Jun 11). `launch/` is untracked + NOT in the sdist exclude /
SENSITIVE_PATTERNS gate yet — keep it untracked or add it before any commit (repo is public).
No code/tests touched.

## [2026-06-06] plan | fantasy-platform analysis (launch/ 08–10) from new_websites.md
Analyzed the fantasy-app list/feature-breakdown in `new_websites.md` along 3 axes and added 3
local-only plan files. (08 data-sources) Verdict: real-money apps (Dream11/My11Circle/MPL/…) are
closed + ToS/legally sensitive (Indian RMG) → **do not scrape**; but official tournament fantasy
APIs expose real prices/ownership — F1 Fantasy (unofficial, Postman/GitHub libs) is the best fit
(opt-in adapter `SPORTIQ_ENABLE_F1_FANTASY`), FPL API is open but EPL-only (WC needs FIFA WC
Fantasy endpoints, verify at launch), Sorare skipped. Integrate via Adapter→FallbackChain, daily
cache. (09 product roadmap) Feature-convergence → gaps: no football/F1 squad optimizer, no transfer
optimizer, no chip advisor, no price/value tools. Proposed P0 reuse-ILP-across-sports +
`*_optimize_transfers`; P1 chip advisor + football/F1 differentials (need 08 ownership); P2
price-change predictor + circuit profiles + config-driven scoring. All would be Pro-gated INTEL
tools. Out of scope: live-points engine, leagues, social, real-money. (10 positioning) These =
market not rivals → reframe to "cross-platform fantasy edge"; multi-format scoring unlocks all
platforms' users; Premium-subscription model validates our Pro tier; "build a fantasy app" parked
as a separate larger decision (stay the intelligence layer). Grounded via web: FPL bootstrap-static,
F1 Fantasy API, Sorare GraphQL. No code/tests touched.

## [2026-06-06] decision | gitignore + release-gate the local strategy docs (repo is public)
Confirmed scope: stay the MCP intelligence layer (no fantasy app). Locked down the local-only
strategy/brain-dump docs so they can't leak on the public repo. Added to `.gitignore`: `launch/`,
`launch.md`, `marketing.md`, `new_websites.md`, `new.md`, `remaining*.md`, `mcp-builder/`
(`step*.md` was already ignored). Extended the existing defense-in-depth gate to the 3 new risky
paths (`launch/`, `marketing.md`, `new_websites.md`) in both the sdist `exclude` (pyproject) and
`SENSITIVE_PATTERNS` (check_release_build.py). Verified: `git status` shows no exposed untracked
files; `git check-ignore` confirms all paths. No src/tests touched.

## [2026-06-06] lint | pre-launch review — 3 P2 correctness fixes + regression locks
Pre-launch pass (3 parallel read-only agents: secret forensics, code review, infra/packaging).
Secret verdict: clean — no credential ever committed in history/branches/tree; safe to go public.
Fixed 3 minor P2s found in review: `cricket_player_matchup` now returns `NOT_FOUND` (not
`ALL_SOURCES_FAILED`) when a player genuinely doesn't exist; `f1_head_to_head_pace` returns
`faster_driver: null` on an exact pace tie (`delta == 0`) instead of defaulting to driver_b;
`simulate_group` / `_draw_qualifiers` now raise a clear `ValueError` on a non-4-team group instead
of a latent `IndexError`. +4 regression tests. Suite 619 → 623 green, ruff clean.

## [2026-06-06] repo-hygiene | untrack internal build/audit docs from the public repo
`git rm --cached` (kept on disk) the internal docs that predated the ignore rules and were still
tracked: `step5–9.md`, `remaining.md`, `AUDIT.md`, `BACKLOG.md`, `changes.md`, `plan.md`,
`docs/hot.md`. Added the five not already covered to `.gitignore`. Removed the now-dead
`See plan.md` reference from `README.md`. No secrets were involved — these stay in old history
(acceptable per the chosen "untrack going forward", not a history rewrite).

## [2026-06-06] decision | reorder to football → F1 → cricket everywhere (order of relevance)
Per request, flipped the long-standing cricket-first convention to **football → F1 → cricket**
everywhere. Code: `server.py` register-call order (MCP clients now list football tools first;
imports stay alphabetical per ruff isort). Docs/prose: README (tagline, flagships, status,
full tool-section block move, dropped out-of-sequence "Phase N" labels), CLAUDE.md tagline +
flagships (+ a note pinning the convention), `docs/index.md` (Tools/Models/Chains/Data-sources
subsections), `src/sportiq/instructions.md` modules table, `pyproject` description + keywords,
`__init__.py` docstring. Verified: 623 tests green, ruff clean, runtime tool list leads with
`football_get_groups`. Prompts order left unchanged (mirror the recipe order; out of scope).

## [2026-06-06] release | launch-readiness — server.json + packaging polish
Authored `server.json` (Official MCP Registry, schema `2025-12-11`, name
`io.github.ninjabeam20/sportiq-mcp`, pypi+stdio+uvx, v0.2.0). Packaging polish: sdist now excludes
the whole `tests/` tree + `evals/` + the untracked dev docs; `check_release_build.py` patterns
generalized (all `step*`, dev docs, `tests/`, `evals/`); classifier `3 - Alpha` → `4 - Beta`;
README gained an env-var table (incl. previously-undocumented `FOOTBALLDATA_KEY`/`REDIS_URL`/
`SPORTIQ_LOG_*`) and POST-PUBLISH placeholders (demo GIF, registry badges). Build gate clean
(wheel + sdist, no sensitive paths). **Remaining manual/post-publish:** register the PyPI Trusted
Publisher (env `pypi`) before tagging `v0.2.0`; after PyPI is live, submit `server.json` via the
`mcp-publisher` CLI and fill the README badge/GIF placeholders.

## [2026-06-08] fix | release workflow PyPI publish gate
v0.2.0 release workflow failed 3× → PyPI never published → `uvx sportiq-mcp` 404s.
Root cause: `uv sync` pinned `--python 3.12` but `.python-version`=3.13, so the `uv run`
test step rebuilt the venv on 3.13 *without* `--extra dev` → `No module named pytest` →
gate crashed before publish. Fix: align all steps to Python 3.13 and pass `--extra dev`
to both `uv run` gate steps. Verified locally: full suite passes + build gate clean.
Re-release requires moving tag v0.2.0 to the fix commit and force-pushing it.

## [2026-06-08] fix | CI missing CBC solver (real test-gate failure)
After the pytest-plumbing fix, the release gate reached pytest and exposed the real
failure: `PulpSolverError: cannot execute cbc`. dream11_solver.py calls `COIN_CMD()`,
which needs a system `cbc` on PATH (present locally via brew, absent on the runner).
Added `apt-get install coinor-cbc` to release.yml and test.yml. Also hardened test.yml
with the same `--python <matrix> --extra dev` flags on its `uv run` steps (it had the
identical venv-rebuild bug across the 3.11/3.12/3.13 matrix). test.yml had been red on
main for the same CBC reason.

## [2026-06-08] release | v0.2.1 — mcp-name marker + registry namespace casing
mcp-publisher publish hit two gates: (1) 403 — namespace is case-sensitive, token grants
`io.github.Ninjabeam20/*` (capital N) but server.json had lowercase → fixed to
`io.github.Ninjabeam20/sportiq-mcp`; (2) 400 — registry requires the literal marker
`<!-- mcp-name: io.github.Ninjabeam20/sportiq-mcp -->` in the *published PyPI* README to
prove ownership. PyPI READMEs are immutable, so added the marker to README.md and bumped
0.2.0→0.2.1 (pyproject + both server.json version fields) to republish. Tag v0.2.1 fires
release.yml → PyPI 0.2.1, then mcp-publisher publish.

## [2026-06-08] decision | attribution = LICENSE file, not username watermarking
User asked to spray `Ninjabeam20` permutations through the codebase to prevent copying.
Declined — ineffective (trivial sed removal; source is public MIT on PyPI by design) and
harms adoption. Real attribution added instead: LICENSE file (MIT, © 2026 Utkarsh Gupta),
README "License & author" section, glama.json (maintainer Ninjabeam20). Registry namespace
`io.github.Ninjabeam20/*` + PyPI ownership already prevent impersonation. License kept MIT
(user chose, maximizes installs/credit). LICENSE not yet in the published 0.2.1 sdist —
will bundle on next version bump.

## [2026-06-08] tool-added | MCPB (.mcpb) desktop extension
Built a Claude Desktop one-click extension at `mcpb/manifest.json` (+ `mcpb/server/main.py`
launcher). Because the package has heavy native deps (scipy/numpy/pandas/pulp), the bundle
does NOT vendor them — it launches via `uvx sportiq-mcp` (pulls from PyPI), consistent with
the project's existing uvx install story. Requires `uv` on the host. Validates + packs via
`npx @anthropic-ai/mcpb` → `dist/sportiq-mcp.mcpb` (gitignored; release artifact). Excluded
`mcpb/` + `dist/` from the PyPI sdist. Next: user installs into Claude Desktop and submits to
the Claude Connectors Directory (desktop-extension form).

## [2026-06-08] feat | remote streamable-HTTP transport + Dockerfile
Added env-gated HTTP transport to server.py: `SPORTIQ_TRANSPORT=http` serves streamable-HTTP
on 0.0.0.0:$PORT (endpoint /mcp); stdio stays the default (uvx contract intact). Dockerfile
installs from source (so it has the HTTP entrypoint) + apt coinor-cbc for the Dream11 solver;
CMD `python -m sportiq.server`. Verified locally without Docker: POST /mcp initialize → 200 with
valid MCP handshake. Deploy target = container host (Cloud Run/Fly/Render), NOT Cloudflare
Workers (free tier blocks Python + can't run the native scipy/numpy/pulp+cbc stack). Cannot
deploy from here (needs the user's cloud login). Quota note: deploy WITHOUT live-data API keys
so the public endpoint only powers the keyless sim/prediction/fantasy tools — avoids strangers
burning rate-limited quotas.

## [2026-06-09] docs | cloud.md deploy runbook + README remote section
Added repo-root cloud.md: step-by-step Google Cloud Run deploy (Part 1 deploy / Part 2
connect to claude.ai+ChatGPT / Part 3 maintenance). Region us-central1 (user chose global
audience). README gained a "Remote / self-hosted" section linking cloud.md + explaining
SPORTIQ_TRANSPORT=http; fixed stale "post-release" uvx comment (package is live). Deploy
itself is user-run (needs their GCP login). Not Cloudflare/Railway-free (RAM/runtime limits).

## [2026-06-09] docs | README/SECURITY state sync for live Cloud Run instance
Server is live on Cloud Run (verified: POST /mcp initialize → serverInfo sportiq v1.27.2).
Synced docs to reality: README gained a "Use the hosted SportIQ" section (live URL + exact
claude.ai and ChatGPT/Developer-Mode connection steps), an "Is it safe to use?" section
(open-source/MIT, read-only, no data collection, no keys on host, meta.is_stale freshness
flagging), a top-of-README "Try it now" callout, and a self-host subsection. Removed the stale
"Transport: stdio only / no remote endpoint" paragraph (now false) and added SPORTIQ_TRANSPORT
to the env-var table. SECURITY.md gained a "Hosted deployment" section documenting the keyless
public instance + the intentional DNS-rebinding-protection disable in HTTP mode. cloud.md gained
the curl gcloud-install fallback (brew cask fails on newer macOS). Committed the server.py
DNS-rebinding fix + uv.lock that the live deploy already runs.
