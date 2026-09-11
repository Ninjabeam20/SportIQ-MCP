# grokbot2 — Tier A crashes

| Field | Value |
|---|---|
| Repo | `sportiq-mcp (Ninjabeam20/SportIQ-MCP)` |
| Branch | `bot` |
| Base SHA | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` |
| Date | 2026-09-11 |
| Scope | Plans only in this commit; no production code yet |

## Goal
Eliminate Tier A crash classes proven RED on base.

## Non-goals
- No Tier B cache/unwrap here
- No deploy

## Safety (binding)
- Implement only on branch `bot` (worktree). Never merge to main, never push, never deploy unless the user explicitly says yes.
- No live scrape / live LLM / live SSH / live paid API hammering unless the user explicitly asks.
- Prefer offline fixtures under `tests/fixtures/**`.
- TDD: failing test first (RED) → minimal fix (GREEN) → tidy.
- Do not stage `.env`, credentials, tokens, or secrets.

## Ranked tasks

### SQ-A1 — pit compound crash

- **Finding ID:** `SQ-A1`
- **File pins:**
  - `src/sportiq/f1/models/pit_strategy.py`
  - `tests/unit/test_pit_strategy.py`
  - `docs/wiki/models/pit-strategy.md`
- **RED repro idea:** Compound/undercut pit sequence with malformed stint list or None compound raises TypeError/ZeroDivision.
- **Failing-test-first steps:**
  1. RED: empty stints / None compound / single-stop edge.
  2. Guard arithmetic + validate inputs → error envelope.
  3. GREEN.
- **Acceptance criteria:**
  - No uncaught exception from pit model on bad input.
  - Tool returns INVALID_INPUT or safe empty plan.
- **Risk:** Medium.
- **Implement only on `bot`:** yes

### SQ-A2 — gather envelopes crash

- **Finding ID:** `SQ-A2`
- **File pins:**
  - `src/sportiq/core/tool_response.py`
  - `src/sportiq/core/fallback.py`
  - `src/sportiq/server.py`
  - `tests/unit/test_tool_telemetry.py`
- **RED repro idea:** asyncio.gather / multi-tool path where one adapter returns non-dict / exception leaks past envelope wrapper.
- **Failing-test-first steps:**
  1. RED: mock gather child raising + returning bare list.
  2. Ensure every path goes through error_envelope/Envelope.
  3. GREEN.
- **Acceptance criteria:**
  - HTTP/MCP layer always returns 3-key envelope; no raw traceback payload.
  - Telemetry still records failure.
- **Risk:** High — shared envelope path.
- **Implement only on `bot`:** yes

### SQ-A3 — cricket NotFound mishandling

- **Finding ID:** `SQ-A3`
- **File pins:**
  - `src/sportiq/core/errors.py:52`
  - `src/sportiq/core/fallback.py:158-216`
  - `tests/chains/test_chain_not_found.py`
  - `src/sportiq/cricket/**`
- **RED repro idea:** All adapters NotFound incorrectly becomes ALL_SOURCES_FAILED or uncaught.
- **Failing-test-first steps:**
  1. RED chain where every adapter raises NotFoundError.
  2. Assert NotFoundError / NOT_FOUND envelope, not crash.
  3. GREEN.
- **Acceptance criteria:**
  - Pure NotFound → NOT_FOUND envelope.
  - Mixed fail vs not-found taxonomy preserved.
- **Risk:** Medium.
- **Implement only on `bot`:** yes

### SQ-A4 — Dream11 CBC / solver crash

- **Finding ID:** `SQ-A4`
- **File pins:**
  - `src/sportiq/cricket/models/dream11_solver.py`
  - `tests/unit/test_dream11_solver.py`
  - `tests/unit/test_dream11_scoring.py`
- **RED repro idea:** CBC/constraint solve with infeasible squad or non-int credits crashes.
- **Failing-test-first steps:**
  1. RED: infeasible constraints; fractional credits; empty player pool.
  2. Return structured infeasible result; no solver traceback.
  3. GREEN.
- **Acceptance criteria:**
  - Infeasible → clear error/empty team flag.
  - No native CBC abort uncaught in tool layer.
- **Risk:** High — native solver edge.
- **Implement only on `bot`:** yes

### SQ-A5 — value-bet crash on bad odds

- **Finding ID:** `SQ-A5`
- **File pins:**
  - `src/sportiq/core/value_bet.py`
  - `src/sportiq/football/models/value_bet.py`
  - `tests/unit/test_value_bet.py`
  - `tests/tools/test_cricket_value_bets.py`
- **RED repro idea:** Odds ≤1, None prob, or empty markets → ZeroDivision/TypeError.
- **Failing-test-first steps:**
  1. RED matrix of illegal odds/probs.
  2. Validate; skip or error envelope.
  3. GREEN.
- **Acceptance criteria:**
  - No crash on odds<=1 or None.
  - Valid value bets still computed.
- **Risk:** Medium.
- **Implement only on `bot`:** yes

### SQ-A6 — form-trends int coercion crash

- **Finding ID:** `SQ-A6`
- **File pins:**
  - `src/sportiq/football/models/form_trends.py`
  - `tests/unit/test_form_trends.py`
  - `tests/tools/test_football_form_trends.py`
- **RED repro idea:** String/float form markers where int expected → ValueError crash.
- **Failing-test-first steps:**
  1. RED: 'W','D', None, '2' mixed series.
  2. Coerce safely; drop/flag bad points.
  3. GREEN.
- **Acceptance criteria:**
  - Non-int points do not crash trends tool.
  - Document coercion rules in test.
- **Risk:** Low.
- **Implement only on `bot`:** yes
## Checklist (all unchecked initially)

- [ ] SQ-A1 pit
- [ ] SQ-A2 gather envelopes
- [ ] SQ-A3 cricket NotFound
- [ ] SQ-A4 Dream11 CBC
- [ ] SQ-A5 value-bet
- [ ] SQ-A6 form-trends int
- [ ] Tier A GREEN on bot
- [ ] main untouched
