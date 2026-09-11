# grokbot3 — Tier B empty-200 cache poison + CricAPI unwrap + IN_PLAY

| Field | Value |
|---|---|
| Repo | `sportiq-mcp (Ninjabeam20/SportIQ-MCP)` |
| Branch | `bot` |
| `main` SHA (do not move) | `5cfa12ff2d8eabd10a279074b3e3b1107e38886d` |
| Recheck date | 2026-09-11 |
| Recheck model | `cursor-grok-4.6-high` (NORMAL, not fast) |
| Scope | Plans only in the recheck commit; Composer 2.5 implements residuals later |

## Goal
Fix **remaining** wrong-result / cache-poison classes. Do not break documented empty-success contracts (off-season live matches, The Odds empty `events`).

## Non-goals
- No Cloud Run / Dell / cloudbuild
- No live CricAPI / football-data.org / The Odds
- No rewrite of `_unwrap` if tests already prove it (SQ-B2)
- No cricket `IN_PLAY` enum invention

## Safety (binding)
Same as grokbot1. Adapter empty-that-means-miss → `NotFoundError` so the chain walks. Genuine empty market → success list + normal TTL.

## Recheck notes (2026-09-11)

`FallbackChain._fetch_uncached` L189 **always caches a successful adapter return**, including empty lists. That is correct when empty is a real answer. Poison is **failure-as-success** (empty because the source does not have the entity / quota / uncovered season). api_football fixtures+squad and CricAPI `_unwrap` already raise `NotFoundError` on that shape. Remaining analog: **football-data.org empty `matches`/`standings`**.

---

### SQ-B1 — empty-200 cache poison

- **Finding ID:** `SQ-B1`
- **Status:** **PARTIAL**
- **File pins:**
  - `src/sportiq/core/fallback.py` L189 — `cache.set` on success; **do not add a global “never cache empty” rule**
  - `src/sportiq/football/adapters/api_football.py` L40–47 fixtures, L153–157 squad — **already GREEN** (`NotFoundError` on empty)
  - `src/sportiq/football/adapters/football_data_org.py` — `FootballDataOrgFixturesAdapter.fetch` L30–58 returns `{"fixtures": []}` on empty `matches` with HTTP 200; **no NotFoundError**. Same for standings L64+ if `standings` empty. This **can cache empty and shadow openfootball / derived_standings** for `fresh_ttl`.
  - `tests/adapters/test_football_data_org.py` — shape tests only; no empty-200 case
  - `tests/unit/test_cache.py`, `tests/unit/test_o3_cache_ttls.py`, `tests/unit/test_fallback_chain.py` — TTL/chain; not adapter empty-200
  - Contrast **must stay success:**
    - `CricAPILiveMatchesAdapter` empty `data: []` off-season (`tests/adapters/test_cricapi.py::test_live_matches_adapter_returns_empty_list_off_season`)
    - The Odds empty `events` off-season (wiki + cricket/football odds tools)
- **Failing-test-first:**
  1. RED `test_fixtures_adapter_empty_matches_raises_not_found` in `tests/adapters/test_football_data_org.py` — respx 200 `{"matches": []}` → `NotFoundError`.
  2. RED `test_standings_adapter_empty_table_raises_not_found` — 200 with empty standings list/blocks → `NotFoundError`.
  3. GREEN: raise `NotFoundError` when the payload has no usable rows (mirror api_football comment: empty must not count as success). Constructor still never raises on missing token.
  4. Do **not** change `FallbackChain` cache.set.
- **Acceptance:**
  - Empty FD.org fixtures/standings walk the chain (openfootball / derived_standings / static).
  - Off-season CricAPI live `[]` and The Odds `events: []` still success.
- **Do not:** raise NotFound on OpenF1 empty laps/sessions (often the only source; empty session is a valid miss at tool layer already). Optional follow-up only if Composer hits a proven OpenF1 dict-as-list wrap bug — out of this ranked list.
- **Risk:** High if someone globally stops caching empty.
- **Implement only on `bot`:** yes

---

### SQ-B2 — CricAPI envelope unwrap

- **Finding ID:** `SQ-B2`
- **Status:** **GREEN** (verify-only)
- **File pins:**
  - `src/sportiq/cricket/adapters/cricapi.py` — `_unwrap` L30–42; live/scorecard/points/player use it; squad L147–156 raises on falsy `series_id` and `status != success`
  - `tests/adapters/test_cricapi.py` — `test_live_matches_adapter_raises_not_found_on_failure_envelope`, `test_scorecard_adapter_raises_not_found_on_failure_envelope`, `test_squad_adapter_raises_without_series_id`, apikey stripped on scorecard/points/player
  - `tests/fixtures/cricapi/match_scorecard_failure.json`
  - `docs/wiki/findings/cricapi-envelope-leak.md` — already describes the fix (last_updated 2026-05-30)
  - `tests/tools/test_cricket_raw_tools.py` — scorecard/points `NOT_FOUND`
- **Composer 2.5:** **do not rewrite `_unwrap`.** Optional extra RED only if nested `{data: {data: ...}}` is observed in a fixture — none of the committed fixtures show a double domain wrap after `_unwrap`. Do not “unwrap twice” blindly (would break list-shaped `data` for live matches).
- **Acceptance:** existing adapter tests still pass; apikey never in adapter output.
- **Risk:** High only if rewritten. Leave it.
- **Implement only on `bot`:** verify-only

---

### SQ-B3 — IN_PLAY state honesty

- **Finding ID:** `SQ-B3`
- **Status:** **PARTIAL**
- **File pins (narrowed — do not use `src/sportiq/core/**` or `cricket/**` as pins):**
  - `src/sportiq/football/models/results_state.py` — `_FINISHED_STATUSES` L115–120, `_is_finished` L123–128, comment L115–119 (in-play scores must not lock)
  - `tests/unit/test_results_state.py` — `test_in_play_score_not_locked` L98–103, `test_scheduled_fixture_ignored`, `test_api_football_ft_status_counts_as_finished` **already GREEN**
  - `src/sportiq/football/models/form_trends.py` — score-present only; **residual** (implement with SQ-A6)
  - Cricket live tools pass through adapter `status` strings. There is **no** project `IN_PLAY` classifier for cricket. Do not add one in this tier.
- **What is already GREEN:** Monte Carlo / Elo live-conditioning will not lock `status=IN_PLAY` group results.
- **Residual:** `compute_form_trends` will count an in-play scoreline as a completed W/D/L. See grokbot2 SQ-A6 tests.
- **Failing-test-first:** do **not** duplicate results_state tests. Add form_trends `test_in_play_scores_not_counted_as_form` only (SQ-A6).
- **Acceptance:**
  - Terminal (`FINISHED`/`FT`/`AET`/`PEN`/`AWD`/`WO`) still count when scores present.
  - `IN_PLAY` never increments `matches_analysed`.
  - `results_state.py` unchanged unless a new provider status appears (out of scope).
- **Do not:** cache-invalidate “on terminal states” in `FallbackChain` — TTL already differs per chain; do not bypass cache.
- **Risk:** Medium if form is wrong in-tournament; low for results_state.
- **Implement only on `bot`:** yes (form_trends only)

## Checklist

- [x] SQ-B1 FD.org empty → NotFoundError
- [x] SQ-B2 CricAPI unwrap (verify-only)
- [x] SQ-B3 IN_PLAY via form_trends (with A6); results_state already GREEN
- [x] Tier B residuals GREEN
- [x] `main` untouched
