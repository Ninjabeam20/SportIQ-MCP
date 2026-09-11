# grokbot3 — Tier B empty-200 cache poison + CricAPI unwrap + IN_PLAY

| Field | Value |
|---|---|
| Repo | `sportiq-mcp (Ninjabeam20/SportIQ-MCP)` |
| Branch | `bot` |
| Base SHA | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` |
| Date | 2026-09-11 |
| Scope | Plans only in this commit; no production code yet |

## Goal
Fix wrong-result / cache-poison classes that return HTTP 200 with bad data.

## Non-goals
- No Cloud Run changes
- No live CricAPI unless fixtures insufficient and user asks

## Safety (binding)
- Implement only on branch `bot` (worktree). Never merge to main, never push, never deploy unless the user explicitly says yes.
- No live scrape / live LLM / live SSH / live paid API hammering unless the user explicitly asks.
- Prefer offline fixtures under `tests/fixtures/**`.
- TDD: failing test first (RED) → minimal fix (GREEN) → tidy.
- Do not stage `.env`, credentials, tokens, or secrets.

## Ranked tasks

### SQ-B1 — empty-200 cache poison

- **Finding ID:** `SQ-B1`
- **File pins:**
  - `src/sportiq/core/fallback.py`
  - `tests/unit/test_cache.py`
  - `tests/unit/test_o3_cache_ttls.py`
  - `tests/unit/test_fallback_chain.py`
- **RED repro idea:** Adapter returns empty body with HTTP 200; result cached and poisons subsequent calls.
- **Failing-test-first steps:**
  1. RED: 200+empty then assert not cached as success (or short TTL + miss marker).
  2. Distinguish empty-success vs error for cache key/TTL.
  3. GREEN with TTL tests.
- **Acceptance criteria:**
  - Empty 200 does not permanently poison cache.
  - Next call can refresh or returns explicit empty meta.
- **Risk:** High — correctness of live tools.
- **Implement only on `bot`:** yes

### SQ-B2 — CricAPI envelope unwrap

- **Finding ID:** `SQ-B2`
- **File pins:**
  - `src/sportiq/cricket/adapters/cricapi.py`
  - `tests/adapters/test_cricapi.py`
  - `docs/wiki/findings/cricapi-envelope-leak.md`
  - `tests/fixtures/cricapi`
- **RED repro idea:** Double-wrapped `{data:{data:...}}` or status envelope leaks to tool consumers.
- **Failing-test-first steps:**
  1. RED fixture with nested envelope / status:failure.
  2. Unwrap once; map failure to NotFound/error.
  3. GREEN + update finding doc if fixed.
- **Acceptance criteria:**
  - Adapter returns domain objects, not raw API envelope.
  - Failure status never looks like success list.
- **Risk:** High.
- **Implement only on `bot`:** yes

### SQ-B3 — IN_PLAY state honesty

- **Finding ID:** `SQ-B3`
- **File pins:**
  - `src/sportiq/core/**`
  - `tests/unit/test_results_state.py`
  - `src/sportiq/cricket/**`
  - `src/sportiq/football/**`
- **RED repro idea:** Finished or scheduled matches labelled IN_PLAY (or inverse) due to stale cache/state map.
- **Failing-test-first steps:**
  1. RED state transitions: scheduled→in_play→finished with clock edges.
  2. Fix classifier; invalidate cache on terminal states.
  3. GREEN.
- **Acceptance criteria:**
  - Terminal matches never reported IN_PLAY.
  - Meta includes state source/staleness.
- **Risk:** Medium.
- **Implement only on `bot`:** yes
## Checklist (all unchecked initially)

- [ ] SQ-B1 cache poison
- [ ] SQ-B2 CricAPI unwrap
- [ ] SQ-B3 IN_PLAY
- [ ] Tier B GREEN
- [ ] main untouched
