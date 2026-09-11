# grokbot2 — Tier A crashes

| Field | Value |
|---|---|
| Repo | `sportiq-mcp (Ninjabeam20/SportIQ-MCP)` |
| Branch | `bot` |
| `main` SHA (do not move) | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` |
| Recheck date | 2026-09-11 |
| Recheck model | `cursor-grok-4.6-high` (NORMAL, not fast) |
| Scope | Plans only in the recheck commit; Composer 2.5 implements residuals later |

## Goal
Eliminate **residual** Tier A crash classes. Do not re-litigate GREEN handlers.

## Non-goals
- No Tier B cache/unwrap except where grokbot1 says A6 shares a file with B3
- No deploy, no merge to `main`
- No wrapping unexpected exceptions as `INVALID_INPUT`

## Safety (binding)
Same as grokbot1. Models pure. Tools use `error_envelope`. TDD on `bot`.

## Recheck notes (2026-09-11)

Original text said “proven RED on base.” Static recheck: **not true for A2/A3-chain/A4-infeasible/A5-None**. Residual holes are real but narrower. Composer 2.5: implement only the **Composer 2.5** subsection of each finding.

---

### SQ-A1 — pit compound / rainfall crash

- **Finding ID:** `SQ-A1`
- **Status:** **RESIDUAL RED**
- **File pins:**
  - `src/sportiq/f1/models/pit_strategy.py` — `predict()` L48–67, L63
  - `src/sportiq/f1/data/tyres.py` — `TyreCompound` StrEnum (`SOFT|MEDIUM|HARD|INTER|WET`)
  - `src/sportiq/f1/intel_tools.py` — `f1_predict_pit_strategy` calls `_predict_strategy` after gather (does **not** catch model `ValueError`/`TypeError`)
  - `tests/unit/test_pit_strategy.py` — happy path only; no dirty-stint cases
  - `docs/wiki/models/pit-strategy.md` — update in SQ-D1 after GREEN
- **What is already GREEN:** empty `stints` → default `"MEDIUM"` (L49–50). `remaining <= 0` early return (L39–46). Tool arg validation for `current_lap`/`total_laps`.
- **Residual RED (do these):**
  1. L52: `latest.get("compound", "MEDIUM").upper()` — if key exists and value is `None` → `TypeError`.
  2. L66: `TyreCompound(current_compound)` — unknown string (`"UNKNOWN"`, `"INTERMEDIATE"`) → `ValueError`.
  3. L63: `float(w.get("rainfall", 0))` — if `rainfall` is `None` → `TypeError`.
- **Failing-test-first (add to `tests/unit/test_pit_strategy.py`):**
  1. RED `test_predict_none_compound_does_not_raise` — stint `{"compound": None, "lap_start": 1}`.
  2. RED `test_predict_unknown_compound_does_not_raise` — stint `compound="UNKNOWN"`.
  3. RED `test_predict_none_rainfall_does_not_raise` — weather `{"rainfall": None}`.
  4. GREEN: coerce `None`/blank compound → `"MEDIUM"`; unknown enum → `"MEDIUM"` (do **not** invent new compounds); `rainfall is None` → `0`. Still return the 4-key dict. **No envelope inside the model.**
- **Acceptance:**
  - `predict(...)` never raises on the three dirty inputs above.
  - Existing `test_one_stop_on_degrading_soft` / `test_rain_triggers_inter_stop` still pass.
  - Tool layer unchanged unless a new test proves it still 500s after the model guard.
- **Risk:** Medium (flagship `f1_predict_pit_strategy`).
- **Do not:** change `TyreCompound` members; call live OpenF1; “fix” gather in this finding.
- **Implement only on `bot`:** yes

---

### SQ-A2 — gather envelopes crash

- **Finding ID:** `SQ-A2`
- **Status:** **MOSTLY GREEN** (verify-only)
- **File pins (corrected):**
  - `src/sportiq/f1/intel_tools.py` — `asyncio.gather(..., return_exceptions=True)` at ~L87, L164, L233, L377, L497, L548; `AllSourcesFailedError`/`NotFoundError` → `error_envelope`; other `BaseException` **re-raised** (~L390–391, L398–399)
  - `src/sportiq/football/intel_tools.py` — value-bet gather ~L412–427, same pattern
  - `src/sportiq/cricket/intel_tools.py` — `_candidate_pool` gather ~L64 **without** `return_exceptions`, but callers wrap `AllSourcesFailedError`/`NotFoundError`/`InvalidInputError` (~L140–153)
  - `src/sportiq/core/tool_telemetry.py` — L79–89 log `outcome=exception` then **`raise`** (keep this)
  - `src/sportiq/core/tool_response.py` — envelope helpers; **do not rewrite**
  - `src/sportiq/server.py` — **drop as a pin**; registration only
  - `tests/unit/test_tool_telemetry.py` — telemetry, not gather envelopes
  - `tests/tools/test_f1_intel_tools.py` — already covers enrichment NotFound
- **What is already GREEN:** expected chain misses become envelopes on F1 pit/tyre and football value-bet gathers.
- **Do not “fix”:** converting telemetry or unknown `BaseException` into `{error}` — that hides bugs and fights `test_tool_telemetry`.
- **Composer 2.5:** skip code unless a targeted test is missing. Optional verify-only: `test_f1_predict_pit_strategy_laps_not_found_returns_envelope` in `tests/tools/test_f1_intel_tools.py` if not already present (check file before adding). Cricket `_candidate_pool` does not need `return_exceptions=True`.
- **Acceptance:** no new swallow-all wrapper; `main` untouched.
- **Risk:** High only if someone rewrites the shared envelope path — **so don’t**.
- **Implement only on `bot`:** yes (tests only if missing)

---

### SQ-A3 — cricket NotFound mishandling

- **Finding ID:** `SQ-A3`
- **Status:** **CHAIN GREEN; cricket RAW LATENT**
- **File pins:**
  - `src/sportiq/core/fallback.py` L212–219 — all-`NotFoundError` → `NotFoundError` (not `AllSourcesFailedError`)
  - `src/sportiq/core/errors.py` L52 — `NotFoundError`
  - `tests/chains/test_chain_not_found.py` — `test_chain_propagates_not_found_when_all_attempts_not_found` + mixed → `AllSourcesFailedError` **already GREEN**
  - `src/sportiq/cricket/tools.py` — **scorecard L71–83 and points_table L103–121 already catch `NotFoundError`**
  - LATENT (copy that pattern):
    - `cricket_get_live_matches` L43–51 — only `AllSourcesFailedError`
    - `cricket_get_schedule` L145–152 — only `AllSourcesFailedError`
    - `cricket_get_squad` L173–180 — only `AllSourcesFailedError` (squad chain usually hits `static_seed`; still catch for contract)
    - `cricket_get_live_odds` L206–214 — only `AllSourcesFailedError`
  - `tests/tools/test_cricket_raw_tools.py` — `test_get_scorecard_not_found_returns_envelope`, `test_get_points_table_not_found_returns_envelope` exist; squad unknown team is **success via static_seed** (`test_cricket_get_squad_unknown_team_returns_envelope`) — do not turn that into `NOT_FOUND`
- **GAPS.md #3** claims cricket tools catch NotFound everywhere — **stale vs these four RAW tools**. SQ-D1 should correct GAPS after the catch-up, not in this recheck.
- **Failing-test-first (patch chain.fetch like the scorecard test):**
  1. RED `test_get_live_matches_not_found_returns_envelope`
  2. RED `test_get_schedule_not_found_returns_envelope`
  3. RED `test_get_live_odds_not_found_returns_envelope`
  4. Optional `test_get_squad_not_found_returns_envelope` **only** when the mock chain raises `NotFoundError` (not for unknown team + real static_seed).
  5. GREEN: `except (AllSourcesFailedError, NotFoundError)` / separate `except NotFoundError` **copy scorecard**. `code="NOT_FOUND"` for NotFound, `ALL_SOURCES_FAILED` otherwise. Use `error_envelope`.
- **Acceptance:**
  - Pure chain `NotFoundError` → `{error.code: NOT_FOUND}` on the four RAW tools.
  - Mixed failure taxonomy unchanged (`test_chain_raises_all_sources_failed_when_a_non_not_found_failure_mixes_in`).
  - `cricket_get_squad("Nowhere United XI")` still succeeds via `static_seed`.
- **Do not:** change `FallbackChain` NotFound walk; touch football/F1 tools (already catch both).
- **Risk:** Medium.
- **Implement only on `bot`:** yes

---

### SQ-A4 — Dream11 CBC / solver crash

- **Finding ID:** `SQ-A4`
- **Status:** **MOSTLY GREEN; residual = missing CBC / solver abort**
- **File pins:**
  - `src/sportiq/cricket/models/dream11_solver.py` — `solve()`; infeasible → `InvalidInputError` L129–132; `<11` candidates L61–64; unknown strategy L57–60
  - `src/sportiq/cricket/intel_tools.py` — `solve as _solve_dream11`; `except InvalidInputError` → `error_envelope(INVALID_INPUT)` L150–151
  - `tests/unit/test_dream11_solver.py` — infeasible credit/WK/team-cap + `<11` **already GREEN**
  - `tests/unit/test_dream11_scoring.py` — scoring constants; **do not retune**
- **What is already GREEN:** infeasible ILP and small pools do not traceback at the tool if they raise `InvalidInputError`.
- **Residual:** `prob.solve(COIN_CMD(msg=False))` L128 — missing `cbc` on PATH (or PuLP solver error) is **not** converted; can leak `PulpSolverError` / `PulpError` past the tool `except InvalidInputError`.
- **Failing-test-first:**
  1. RED `test_solver_missing_cbc_raises_invalid_input` in `tests/unit/test_dream11_solver.py` — monkeypatch `COIN_CMD` / `prob.solve` to raise a generic `Exception("cbc not found")` (do not require a real missing binary in CI).
  2. GREEN: in `solve()`, catch solver failures and re-raise `InvalidInputError` with a message that names CBC on PATH. Do **not** return an empty XI dict on infeasible (keep raise; tool already envelopes).
- **Acceptance:**
  - Infeasible → `InvalidInputError` (existing tests).
  - Simulated CBC abort → `InvalidInputError`, then tool `{error.code: INVALID_INPUT}`.
  - No CBC install in CI; happy-path tests still need `coinor-cbc` as today.
- **Do not:** switch to OR-Tools; change role bounds; catch at telemetry layer.
- **Risk:** High (native solver) — keep the catch **inside `solve()`**.
- **Implement only on `bot`:** yes

---

### SQ-A5 — value-bet crash on bad odds

- **Finding ID:** `SQ-A5`
- **Status:** **PARTIAL**
- **File pins:**
  - `src/sportiq/core/value_bet.py` — canonical `implied_prob` / `find_value` (football module is a re-export)
  - `src/sportiq/football/models/value_bet.py` — re-export only; **do not duplicate logic**
  - `src/sportiq/football/intel_tools.py` — `football_find_value_bets` L457–458 calls `find_value` **without** catching `ValueError`
  - `tests/unit/test_value_bet.py` — `test_implied_prob_rejects_nonpositive`, `test_find_value_skips_missing_price` exist
  - `tests/tools/test_cricket_value_bets.py` — cricket tool; value_bets empty until win model; **low relevance**
- **What is already GREEN:** `None` prices skipped (`bookmaker.get(outcome) is not None`). `devig({})` → `{}`. `implied_prob(0)` raises `ValueError` **by design**.
- **Residual:** `find_value` still calls `implied_prob` on **any non-None** price. `home=0`, `home=-1`, or non-numeric → `ValueError`/`TypeError` aborts the whole `football_find_value_bets` scan.
- **Clarification:** decimal odds `== 1.0` is **valid** (`implied_prob=1.0`). Do **not** treat `<= 1` as illegal. Illegal = `<= 0` or non-numeric.
- **Failing-test-first (`tests/unit/test_value_bet.py`):**
  1. RED `test_find_value_skips_nonpositive_odds` — bookmaker `home=0` or `home=-1`; function returns list (possibly empty), **does not raise**.
  2. RED `test_find_value_skips_non_numeric_odds` — `home="bad"`.
  3. Keep `test_implied_prob_rejects_nonpositive` (direct call still raises).
  4. GREEN: in `find_value` only, skip outcomes whose price is `<= 0` or not coercible to `float`. Do not change `implied_prob` contract.
- **Acceptance:** one bad bookmaker price cannot crash the tool; valid 1X2 still flags value (`test_find_value_flags_positive_edge`).
- **Do not:** edit cricket value-bet tool to invent a cricket win model (wiki: list stays empty until wired).
- **Risk:** Medium.
- **Implement only on `bot`:** yes

---

### SQ-A6 — form-trends int coercion crash

- **Finding ID:** `SQ-A6`
- **Status:** **PARTIAL** (share file with SQ-B3)
- **File pins:**
  - `src/sportiq/football/models/form_trends.py` — L32–36 score-present gate; L50–51 `int(fx["home_goals"])` / `int(away_goals)`
  - `src/sportiq/football/models/results_state.py` — `_FINISHED_STATUSES` / `_is_finished` (reuse; do not fork a third set)
  - `src/sportiq/football/intel_tools.py` — `football_form_trends` L509–510 calls model with no extra try
  - `tests/unit/test_form_trends.py` — ints only
  - `tests/tools/test_football_form_trends.py` — tool wiring
  - `docs/wiki/models/form-trends.md` — **stale**: claims `recent_trend` needs ≥6 matches; code uses ≥4 (comment L81–83). xG “0.0 if no data” vs code `None`. Fix in SQ-D1, **do not change the ≥4 rule**.
- **Residual:**
  1. Non-int goals (`"FT"`, `""`) → `ValueError`.
  2. **SQ-B3 overlap:** in-play fixtures with live scores are treated as completed because the model ignores `status` (results_state already does not).
- **Failing-test-first (`tests/unit/test_form_trends.py`):**
  1. RED `test_non_int_goals_skipped_not_crashed` — `home_goals="W"` or `"2"` mixed with a valid FT row; no raise; valid row still counts. `"2"` may coerce via `int("2")` — that is OK; document in test.
  2. RED `test_in_play_scores_not_counted_as_form` — `status="IN_PLAY"` with scores present → not in `matches_analysed` (this is the B3 half; implement in the same change set).
  3. GREEN: skip row on `int()` failure; if `status` is present, require membership in `results_state._FINISHED_STATUSES` (import the frozenset; do not copy-paste literals in two files if a one-line import is possible — `form_trends` importing `_FINISHED_STATUSES` from `results_state` is OK). If `status` missing, keep today’s score-present behavior (legacy payloads).
- **Acceptance:** non-int does not crash; IN_PLAY does not enter form; existing form_string tests still pass.
- **Do not:** change `_FINISHED_STATUSES` members without a new fixture adapter status; do not “fix” wiki ≥4 vs ≥6 by changing code to 6.
- **Risk:** Low–medium.
- **Implement only on `bot`:** yes

## Checklist

- [x] SQ-A1 pit dirty telemetry
- [x] SQ-A2 gather envelopes (verify-only)
- [x] SQ-A3 cricket RAW NotFound catch
- [x] SQ-A4 Dream11 missing CBC
- [x] SQ-A5 value-bet skip illegal odds
- [x] SQ-A6 form-trends coerce + finished-status (with B3)
- [x] Tier A residuals GREEN on `bot`
- [x] `main` untouched
