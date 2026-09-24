# grokbot-test-audit — post-impl on `bot`

> **Historical test snapshot (2026-09-11).** Counts, SHAs, and branch status below are from the audited commit; the fixes were merged to main on 2026-09-25.

| Field | Value |
|---|---|
| Repo | `Ninjabeam20/SportIQ-MCP` |
| Branch | `bot` (`git branch --show-current`) |
| Audited SHA | `13e2104` (`fix(bot): Tier A/B residuals from grokbot recheck plans`) |
| `origin/bot` at audit start | `13e2104` (matched local) |
| `main` / `origin/main` | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` — **unchanged**; `HEAD..origin/main` empty |
| Commits on `bot` not on `main` | 3 (`dfe9bf4` plans, `003f8a0` recheck, `13e2104` Composer impl) |
| Audit model | `cursor-grok-4.6-high` NORMAL (`originalModelName` did **not** contain `fast`) |
| Audit date | 2026-09-11 |
| App fixes this pass | **none** |

## Non-goals (honoured)

- No merge to `main`, no deploy, no live sports APIs
- No Elo retune, no Dockerfile / cloudbuild / compose edits
- RED proofs ran from `/tmp/sportiq_audit_reds.py` (not added to the suite)

## Suite

```
git branch --show-current     # bot
git rev-parse --short HEAD    # 13e2104
git rev-parse main            # 5cfa12ff2d8eabd10a279074b3e3b1107e38886d
git diff main -- Dockerfile cloudbuild.yaml docker-compose.yml   # empty

uv run pytest -q --tb=no --disable-warnings
# ======================= 804 passed, 1 warning in 18.35s =======================
```

Warning: `StarletteDeprecationWarning` in `tests/unit/test_client_info_middleware.py:14` (`httpx` + `starlette.testclient`). Pre-existing; not from Composer.

Grokbot4 clusters (A1/A4/A5/A6/A3/B1/B2/A2) are a subset of the 804. Named Composer tests are present and GREEN.

---

## Composer residuals vs grokbot2/3 — status on `13e2104`

| ID | Composer claim | Audit |
|---|---|---|
| SQ-A1 pit compound / rainfall | GREEN | **GREEN for the three named cases.** `None`/blank/unknown compound → `MEDIUM`; `None` rainfall → 0. Tests in `tests/unit/test_pit_strategy.py`. **Residual RED:** non-numeric rainfall still `ValueError` (see R5). |
| SQ-A5 value-bet | GREEN | **GREEN.** `find_value` skips `<=0` and non-numeric; `implied_prob(0)` still raises. Mixed illegal+legal still flags legal outcomes (offline GREEN control). Tests only assert `isinstance(list)` — weak, not wrong. |
| SQ-A4 Dream11 CBC | GREEN | **GREEN at model.** `solve()` wraps solver abort in `InvalidInputError` naming CBC. Tool already maps that to `INVALID_INPUT`. **Coverage gap:** no tool-level envelope test (unit-only). |
| SQ-A6 + SQ-B3 form_trends | GREEN | **GREEN for named cases.** Non-int goals skipped; `IN_PLAY` not in `matches_analysed`; `_FINISHED_STATUSES` imported from `results_state` (no forked set). **Residual RED:** non-numeric **xG** still `ValueError` (see R4). |
| SQ-A3 cricket RAW NotFound | GREEN | **GREEN.** Four RAW tools catch `NotFoundError`; named tests exist. `cricket_get_squad("Nowhere United XI")` still succeeds via `static_seed`. |
| SQ-B1 FD.org empty | GREEN | **PARTIAL.** Fixtures `matches: []` and standings `standings: []` raise `NotFoundError`. **Missed:** scorers adapter still succeeds on empty; `table: None` `TypeError`s instead of walking (R3, R3b). Chain-first **api_football** standings/scorers still empty-success (R2) — worse than the FD.org hole Composer closed. |
| SQ-A2 gather envelopes | verify-only | Pit `NotFound` envelope test added and GREEN. Plan **over-claimed** `return_exceptions=True` at `f1_intel_tools.py` L164/L233 (undercut / h2h) — those still use try/except around gather. Race-pace gather **swallows** unexpected `Exception` as `ALL_SOURCES_FAILED` (R7). |
| SQ-B2 CricAPI unwrap | verify-only | Untouched. Existing adapter tests still GREEN. Finding page still describes the fix. |
| SQ-D1 docs | done | Pit / form / value / dream11 wiki + GAPS #3 **body** updated. Snapshot table + value-bet **path** + weather-strategy **keys** still drift (see Docs). |

`results_state.py` unchanged (correct per B3). Off-season CricAPI live `[]` and The Odds empty `events` not retargeted (correct).

---

## NEW REDs (proven offline, no app fix)

Proof file: `/tmp/sportiq_audit_reds.py` against `13e2104`.
Result: **9 failed, 2 passed** (the 2 are GREEN controls).

### P0 — cache poison / crash in live INTEL

**R2 — api_football standings + scorers empty-200 (chain-first)**
- `APIFootballStandingsAdapter.fetch` returns `{"standings": []}` when `response` is empty. Same free-plan “uncovered WC 2026 season” shape the **fixtures** adapter already treats as `NotFoundError` (comment at `api_football.py` L40–43).
- Standings chain: `api_football → football_data_org → derived_standings`, `fresh_ttl=600`. Empty success **caches 10 min and shadows** FD.org (now a miss) **and** derived standings.
- Scorers chain: `api_football → football_data_org`, `fresh_ttl=86400`. Empty success caches **24h**.
- Proof: `test_api_football_standings_empty_raises_not_found` / `test_api_football_scorers_empty_raises_not_found` → `DID NOT RAISE NotFoundError`.
- Next fix: copy the fixtures empty-`response` guard. Football tools **already** `except (AllSourcesFailedError, NotFoundError)` — GAPS #3 “don’t add adapter guards without widening tools” is **stale** for these two tools.

**R1 — `f1_weather_strategy_impact` None rainfall `TypeError`**
- Twin of SQ-A1 that Composer did **not** patch. `intel_tools.py:292`: `float(w.get("rainfall", 0))` when value is `None`.
- OpenF1 weather samples use `rainfall: 0`; live payloads can send `null`. Tool has no model try/except → FastMCP 500, not envelope.
- Proof: `test_weather_strategy_none_rainfall_does_not_raise` → `TypeError: float() argument ... not 'NoneType'`.
- Next fix: same coerce as `pit_strategy.predict` (`None` → `0.0`); skip/coerce non-numeric while there.

### P1 — incomplete B1 / dirty-input residuals

**R3 — `FootballDataOrgScorersAdapter` empty still success**
- Composer patched fixtures + standings only. Scorers: `return {"scorers": scorers}` with no empty guard (`football_data_org.py:142`).
- Proof: `test_fd_org_scorers_empty_raises_not_found` → `DID NOT RAISE`.
- Next fix: raise `NotFoundError` when no usable rows (mirror standings). Do **not** change `FallbackChain.cache.set`.

**R3b — FD.org standings `table: None` TypeError**
- `for row in block.get("table", [])` — default only applies if key **missing**. `"table": null` iterates `None`.
- Proof: `test_fd_org_standings_null_table_raises_not_found` → `TypeError: 'NoneType' object is not iterable`.
- Next fix: `block.get("table") or []`; empty after flatten → existing `NotFoundError`.

**R4 — form_trends xG not guarded**
- Goals wrapped in `int()` try/except; xG `float(xg_h)` is not. `"n/a"` / `""` crashes the whole team’s form.
- Proof: `test_form_trends_non_numeric_xg_skipped_not_crashed` → `ValueError: could not convert string to float: 'n/a'`.
- Next fix: skip xG fields on coerce failure; still count the match for W/D/L.

**R5 — pit `predict` non-numeric rainfall**
- Composer handled `None` only. `rainfall="oops"` → `ValueError` at L69.
- Proof: `test_predict_non_numeric_rainfall_does_not_raise`.
- Next fix: treat non-coercible rainfall as dry (0), same as None.

**R7 — race-pace gather swallows unexpected exceptions**
- `f1_race_pace_compare` L557–569: any `Exception` from laps gather → `{error.code: ALL_SOURCES_FAILED}` instead of re-raise.
- Violates grokbot1/2: envelope only `AllSourcesFailedError` / `NotFoundError`; telemetry must still see unknowns.
- Proof: `_fetch_driver_laps` `TypeError("boom")` → envelope `ALL_SOURCES_FAILED` (no raise).
- Same pattern: `cricket/intel_tools.py:678` player-matchup stats gather.
- Next fix: re-raise if not `AllSourcesFailedError`/`NotFoundError` (copy pit L390–391).

**R6 — OpenF1 dict-as-list wrap (grokbot3 optional follow-up)**
- `{"laps": data if isinstance(data, list) else [data]}` turns a 200 dict body into one fake lap.
- Proof: `json={"detail": "not found"}` → `{"laps": [{"detail": "not found"}]}`.
- Do **not** raise `NotFoundError` on a true empty **list** (only OpenF1 source; empty session is a valid miss at tool layer). Next fix: if not `list`, treat as empty/`NotFoundError` — never wrap a dict as a one-element collection.

### P2 — docs / plan drift (not crashes)

| Item | Drift |
|---|---|
| `GAPS.md` snapshot row 3 | Still “cricket intel 2026-08-13”; body mentions cricket RAW 2026-09-11. Snapshot table not refreshed. |
| GAPS #3 “Where” | Warns that adding empty-payload `NotFoundError` without widening football/F1 **tools** reopens the envelope contract. Those tools already catch both. Standings/scorers empty-fix does **not** need a tools.py change. |
| `docs/wiki/models/value-bet.md` | Still says math lives in `football/models/value_bet.py`. That file is a re-export; canonical is `src/sportiq/core/value_bet.py`. Skip language is updated. |
| `find_value` docstring | Still “missing (None) price are skipped” — code also skips non-positive / non-numeric. |
| `docs/wiki/tools/f1-weather-strategy-impact.md` | Success example keys `rainfall_detected` / `recommended_compound` / `rationale`. Code+tests: `has_rain` / `compound_recommendation` / `recommendation`. `last_updated: 2026-05-28`. SQ-D1 did not pin this page. |
| `form-trends.md` | “all zeros” for off-season vs `xg_for`/`xg_against` = `None`. Minor. |
| grokbot2 SQ-A2 pins | Listed L87, L164, L233, L377, L497, L548 as `return_exceptions=True`. Only L87, L377, L497, L548 actually pass it. L164/L233 are try/except. |

No “fixed in prod”, no live `*.run.app` in the Composer wiki edits. Connector URL left as `https://sportiq.utkarshgupta.org/mcp`.

### GREEN controls (must not regress)

- `find_value` mixed `{home: 0, draw: 3.0, away: "bad"}` does not raise; home/away omitted.
- `implied_prob(0)` still `ValueError`.
- Named Composer tests listed in grokbot2/3 are in tree and part of the 804.

---

## Ranked next fixes (single-task, `bot` only)

Do **not** bundle. TDD: add the RED test from `/tmp/sportiq_audit_reds.py` into the matching `tests/` file first.

1. **R2** api_football standings + scorers empty → `NotFoundError` (highest cache-poison leverage; tools already envelope).
2. **R1** `f1_weather_strategy_impact` rainfall coerce (crash, INTEL, same class as A1).
3. **R3 + R3b** FD.org scorers empty + null `table` (finish B1).
4. **R4** form_trends xG coerce/skip.
5. **R5** pit non-numeric rainfall.
6. **R7** race-pace (and cricket player-matchup) re-raise unexpected `Exception`.
7. **R6** OpenF1 dict wrap — only if a fixture/cassette shows a dict 200; otherwise defer.
8. Docs: GAPS snapshot + #3 “Where”; value-bet canonical path; weather-strategy keys; `find_value` docstring.

Stop conditions unchanged: no merge to `main`, no deploy, no live paid APIs, no Elo retune, no Dockerfile/cloudbuild/compose.

## Intentionally not treated as bugs

- Cricket `_candidate_pool` gather without `return_exceptions=True` — grokbot2 said skip; callers wrap expected errors.
- The Odds / CricAPI live empty-list success — documented empty market.
- OpenF1 empty **list** success — grokbot3: do not raise NotFound (only source).
- A5 tests not asserting mixed legal+illegal — quality, not a product bug (GREEN control holds).
- A4 missing tool-level CBC envelope test — wiring exists; add test when touching the solver again.
- Broad `except Exception` inside `dream11_solver.solve()` — required by A4; keep it **inside** `solve()`.
