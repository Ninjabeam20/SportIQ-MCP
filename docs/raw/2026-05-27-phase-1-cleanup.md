# Phase 1 cleanup — start here on restart

This is the first thing to read after restarting. Phase 1 (commit `c74464a`) landed 5 cricket RAW tools and 54 green tests, but a Phase-0-↔-Phase-1 alignment review found three runtime bugs and four contract-drift gaps. Decisions already made:

- **Path 2 (full cleanup)** before Phase 2 — covers every block below.
- **Drop** `player_stats_chain` + wiki page + `CricSheetPlayerStatsAdapter`. Revisit in Phase 3 when Dream11 needs player stats.
- **Update the caching-policy rule** to allow readable cache keys (current chain code stays as-is).

All bugs were verified at runtime — see the proof commands in the verification section.

To resume: work the steps in order. Each step has its bug summary, the files to touch, and the test(s) to add. After Step 10, run the verification block at the bottom and commit.

---

## Step 1 — A1: Fix opt-in scraper env vars

**Bug:** `SPORTIQ_ENABLE_NDTV=1` and `SPORTIQ_ENABLE_CRICBUZZ=1` (documented in `.env.example`, README, ADR-0007, CLAUDE.md, hard rules) do not flip the runtime fields. pydantic-settings matches by field name; fields are `enable_ndtv_scraper` / `enable_cricbuzz_scraper` with no prefix, so they match `ENABLE_NDTV_SCRAPER` instead.

**Files:**

- `src/sportiq/config.py:18-19` — give the two fields `validation_alias` set to the documented env var. Keep `Field(default=False, …)`.
- `tests/unit/test_config.py` (new) — `monkeypatch.setenv("SPORTIQ_ENABLE_NDTV", "1")`; reload settings; assert `enable_ndtv_scraper is True`. Symmetric test for cricbuzz.

Do NOT rename the fields — adapters reference `settings.enable_ndtv_scraper` in several places.

---

## Step 2 — A2: Fix `cricket_get_scorecard`

**Bug:** Two combined defects.

1. `live_score_chain.cache_key_fn = lambda **_: "sportiq:cricket:live_score:all"` (`chains.py:63`) collapses every call to the same key — `cricket_get_live_matches()` and `cricket_get_scorecard("abc")` and `cricket_get_scorecard("xyz")` collide.
2. `CricAPIScorecardAdapter` (defined at `cricapi.py:43-51`) is not in any chain. Even with a cache miss, the tool would hit `/currentMatches`.

**Files:**

- `src/sportiq/cricket/adapters/cricapi.py` — keep `CricAPIScorecardAdapter` as-is.
- `src/sportiq/cricket/adapters/rapidapi_cricbuzz.py` — add a small `RapidAPICricbuzzScorecardAdapter` (`/mcenter/v1/{match_id}/scard` endpoint pattern). Stub fixture `tests/fixtures/rapidapi/scorecard.json`.
- `src/sportiq/cricket/chains.py` — add a new module-level `scorecard_chain`:
  ```python
  scorecard_chain = FallbackChain(
      name="cricket:scorecard",
      adapters=[_cricapi_scorecard, _rapidapi_scorecard],
      cache_key_fn=lambda match_id, **_: f"sportiq:cricket:scorecard:{match_id}",
      fresh_ttl=30,
      stale_ttl=300,
  )
  ```
  Also instantiate `_cricapi_scorecard = CricAPIScorecardAdapter()` and `_rapidapi_scorecard = RapidAPICricbuzzScorecardAdapter()` and register them for health.
- `src/sportiq/cricket/tools.py:58` — `cricket_get_scorecard` calls `scorecard_chain.fetch(match_id=match_id.strip())` instead of `live_score_chain`.
- `tests/chains/test_cricket_chains.py` — new `test_scorecard_chain_keys_by_match_id`: different match_ids → different cache keys.
- `tests/adapters/test_cricapi.py` — add `test_scorecard_adapter_fetches_by_id` using `tests/fixtures/cricapi/match_scorecard.json` (fixture already exists).
- `tests/adapters/test_rapidapi_cricbuzz.py` — adapter test for the new RapidAPI scorecard adapter.
- `tests/tools/test_cricket_raw_tools.py:test_get_scorecard_success` — switch the patch target from `live_score_chain` to `scorecard_chain`.
- `docs/wiki/chains/cricket-scorecard-chain.md` — new page.
- `docs/wiki/data-sources/cricapi.md` and `rapidapi-cricbuzz.md` — add `cricket-scorecard-chain` to `related`.
- `docs/index.md` — add scorecard chain row under Chains › Cricket.

---

## Step 3 — A3: Delete dead player_stats path

**Decision:** Drop entirely; revisit in Phase 3.

**Files to delete:**

- `tests/fixtures/cricsheet/player_stats_sample.json`
- `docs/wiki/chains/cricket-player-stats-chain.md`

**Files to edit:**

- `src/sportiq/cricket/adapters/cricsheet.py` — remove `CricSheetPlayerStatsAdapter`. Keep `CricSheetSquadAdapter` (still used by squad chain).
- `tests/adapters/test_cricsheet.py` — remove the `CricSheetPlayerStatsAdapter` tests; keep `CricSheetSquadAdapter` tests.
- `src/sportiq/cricket/chains.py` — remove `_cricsheet_stats` instantiation, its `register_adapter_for_health` entry, the `CricSheetPlayerStatsAdapter` import, and the `player_stats_chain` block.
- `src/sportiq/cricket/tools.py:17` — drop `player_stats_chain` from the import list.
- `docs/index.md` — remove the `cricket-player-stats-chain` line.

---

## Step 4 — B1: Dedupe adapter registration in health

**Bug:** `_registered_adapters` accumulates 13 entries for 6 unique `name`s, so `sportiq_health()` shows `cricapi` four times.

**Files:**

- `src/sportiq/core/health.py:19-21` — in `register_adapter_for_health`, skip if any already-registered adapter has the same `name`. Keep the first instance (which has the healthcheck that exercises the most-common endpoint).
- `tests/unit/test_health.py` (new or extend existing) — register two stub adapters with the same name, assert only one ends up in `_registered_adapters`.

After this fix, `sportiq_health()` will report 6 cricket adapters: `cricapi`, `cricsheet`, `ndtv_sports_scraper`, `cricbuzz_scraper`, `rapidapi_cricbuzz`, `static_seed`.

---

## Step 5 — B2: Wire rate limiting into FallbackChain

**Bug:** `core/ratelimit.py` is unused. `.claude/rules/api-budgets.md` says the chain checks budget before each adapter call. Without this, CricAPI's 100/day cap will be silently burned through.

**Files:**

- `src/sportiq/core/fallback.py` — extend `Adapter` Protocol with optional `budget: Budget | None = None` attribute (Protocols can declare attributes). Before each `adapter.fetch(**kwargs)`, if `adapter.budget` is set, call `await check_and_consume(adapter.budget)`. On `False`: append `{"name": adapter.name, "status": "skipped", "reason": "rate_limited", "duration_ms": 0}` to attempts and `continue`.
- `src/sportiq/cricket/adapters/cricapi.py` — give each `CricAPI*Adapter` class a class-level `budget = Budget(source="cricapi", per_day=100)`. All five share the same budget (same source name → same counter key).
- `src/sportiq/cricket/adapters/rapidapi_cricbuzz.py`, `cricsheet.py`, `ndtv_sports_scraper.py`, `cricbuzz_scraper.py` — set `budget = None` explicitly so the protocol attribute is satisfied without surprising defaults (free-tier limits for these are informal/none).
- `tests/chains/test_chain_respects_budget.py` (new) — stub adapter with `budget = Budget(source="x", per_minute=1)`; call chain twice in the same minute; second call must skip the budgeted adapter and fall to the next.
- `src/sportiq/core/health.py` — expose remaining quota per source in the `quotas` dict (currently `{}`). Iterate `_registered_adapters`, collect distinct budgets, call `remaining()` on each, populate `quotas[source]`.
- `tests/unit/test_health.py` — assert `quotas` includes `cricapi` when a CricAPI adapter is registered with a budget.

---

## Step 6 — B3: Tool registration refactor (`register_X(mcp)` pattern)

**Bug:** `tools.py:12` does `from sportiq.server import mcp` then decorates at module import. Works via Python's partial-module mechanism but is fragile. Phase 0 standard is `register_health_tool(mcp)`.

**Files:**

- `src/sportiq/cricket/tools.py` — define each tool function at module level (bare async def), then add `def register_cricket_tools(mcp): mcp.tool()(cricket_get_live_matches); …` for each. Remove `from sportiq.server import mcp`.
- `src/sportiq/server.py` — replace `import sportiq.cricket.tools` (side-effect) with `from sportiq.cricket.tools import register_cricket_tools` then `register_cricket_tools(mcp)`.
- `tests/tools/test_cricket_raw_tools.py` — no change required (functions still importable as `tools.cricket_get_live_matches`).

---

## Step 7 — B4: Update the caching-policy rule

**Decision:** Readable keys win on debug ergonomics. The rule was written before chains existed.

**Files:**

- `.claude/rules/caching-policy.md:18-21` — replace the "Key pattern" section. New text:
  ```
  ## Key pattern
  
  Keys are `sportiq:{sport}:{category}:{readable_args}` where `readable_args` is a
  colon-joined string of the inputs (e.g. `sportiq:cricket:fixtures:ipl2026`,
  `sportiq:cricket:squad:MI:none`). Use `none` / `all` for absent optional args.
  
  Hashing is only required when args are unbounded or contain user-supplied
  strings that could include `:` or `*` — in that case hash with
  `hashlib.blake2s(..., digest_size=8).hexdigest()`.
  ```
- No code changes — current chain `cache_key_fn`s already match this.

---

## Step 8 — C1: Add `static-seed.md` wiki page + index entry

**Bug:** `[[static-seed]]` is linked from three pages but has no destination.

**Files:**

- `docs/wiki/data-sources/static-seed.md` (new) — frontmatter (`type: data-source`, tags `[cricket, squad, static]`, related includes `[[cricket-squad-chain]]`). Body: what it is (local JSON reader), where data lives (`src/sportiq/cricket/data/squads.json`), the 10 IPL teams shipped, when it serves (always-on terminator), and that `venues.json` arrives in Phase 2.
- `docs/index.md` — add under Data sources › Cricket:
  ```
  - [[static-seed]] — Local JSON reader; always-on squad chain terminator; ships IPL 2026 rosters.
  ```

---

## Step 9 — C2: Resolve CricSheet 404

**Bug:** `https://cricsheet.org/register/people.json` returns 404. `CricSheetSquadAdapter` always fails at runtime.

**Investigation first (time-box: 15 min):**

- `curl -I https://cricsheet.org/register/people.json` — confirm 404.
- Check cricsheet.org for the actual register endpoint. Likely candidates:
  - `https://cricsheet.org/players.csv`
  - `https://cricsheet.org/downloads/` (paged HTML index of tournament JSON zips)
  - The site may have removed the people registry endpoint entirely.

**Outcomes:**

- **If a working JSON endpoint exists:** update `_PEOPLE_URL` in `src/sportiq/cricket/adapters/cricsheet.py:14`; re-record `tests/fixtures/cricsheet/squad_sample.json` to the new shape.
- **If no equivalent exists:** drop `CricSheetSquadAdapter` entirely. The squad chain becomes `cricapi → static_seed`. Update `docs/wiki/chains/cricket-squad-chain.md`, `docs/wiki/data-sources/cricsheet.md` (delete file), `chains.py`, `tools.py`, and the cricsheet adapter test.

---

## Step 10 — C3: Delete `tests/fixtures/__init__.py`

Cosmetic. The directory holds JSON/HTML, not Python modules; pytest doesn't need the `__init__.py`.

```bash
rm tests/fixtures/__init__.py
```

---

## Verification (after all steps)

```bash
# 1. Full suite green. Expected count drifts a bit (more new tests than dropped ones).
uv run pytest

# 2. Env var smoke (A1)
SPORTIQ_ENABLE_NDTV=1 uv run python -c "from sportiq.config import settings; assert settings.enable_ndtv_scraper, 'A1 still broken'"

# 3. Scorecard isolation (A2)
uv run python -c "
from sportiq.cricket import chains
assert chains.scorecard_chain.cache_key_fn(match_id='abc') != chains.scorecard_chain.cache_key_fn(match_id='xyz'), 'A2 still broken'
"

# 4. Health dedup (B1)
uv run python -c "
from sportiq.cricket import chains
from sportiq.core.health import _registered_adapters
names = [a.name for a in _registered_adapters]
assert len(names) == len(set(names)), f'B1 still broken: {names}'
"

# 5. Rate-limit smoke (B2)
uv run python -c "
import asyncio
from sportiq.core.ratelimit import Budget, check_and_consume, remaining
async def go():
    b = Budget(source='__smoke__', per_minute=2)
    assert await check_and_consume(b)
    assert await check_and_consume(b)
    assert not await check_and_consume(b)
asyncio.run(go())
"

# 6. MCP schema (B3 — all 5 cricket tools still listed)
npx @modelcontextprotocol/inspector uvx --from . sportiq-mcp
```

---

## Bug confirmations from the review (so you don't have to re-verify)

```
# A1
enable_ndtv_scraper after SPORTIQ_ENABLE_NDTV=1:    False  (BUG)
enable_ndtv_scraper after ENABLE_NDTV_SCRAPER=1:    True   (actually-matching env)

# A2
live_matches() cache key  : sportiq:cricket:live_score:all
scorecard(abc) cache key  : sportiq:cricket:live_score:all   (BUG: collision)
scorecard(xyz) cache key  : sportiq:cricket:live_score:all   (BUG: collision)
CricAPIScorecardAdapter in live_score_chain? False           (BUG: orphan adapter)

# A3
player_stats_chain referenced in tools.py? False             (BUG: dead chain)

# B1
Total adapter registrations: 13
Unique adapter names      : 6                                (BUG: duplicate health rows)
Duplicates: cricapi 4×, rapidapi_cricbuzz 3×, ndtv_sports_scraper 2×, cricsheet 2×
```

---

## Critical files (quick map)

- `src/sportiq/config.py` (A1)
- `src/sportiq/cricket/chains.py` (A2, A3, B2)
- `src/sportiq/cricket/tools.py` (A2, A3, B3)
- `src/sportiq/cricket/adapters/cricapi.py` (A2, B2)
- `src/sportiq/cricket/adapters/rapidapi_cricbuzz.py` (A2, B2)
- `src/sportiq/cricket/adapters/cricsheet.py` (A3, C2)
- `src/sportiq/cricket/adapters/{ndtv_sports_scraper,cricbuzz_scraper,static_seed}.py` (B2)
- `src/sportiq/core/health.py` (B1, B2 quotas)
- `src/sportiq/core/fallback.py` (B2)
- `src/sportiq/server.py` (B3)
- `.claude/rules/caching-policy.md` (B4)
- `docs/wiki/data-sources/static-seed.md` (C1, new)
- `docs/wiki/chains/cricket-scorecard-chain.md` (A2, new)
- `docs/wiki/chains/cricket-player-stats-chain.md` (A3, delete)
- `docs/index.md` (C1, A2, A3)

---

## When you finish

Per CLAUDE.md Rule #8, end the session with the standard format:

```
**Files added:** …
**Files modified:** …
**Intentionally not touched:** …
**Follow-up needed:** …
```

Then append a single line to `docs/log.md`:

```
## [YYYY-MM-DD] cleanup | Phase 1 alignment pass
Fixed A1 (env aliases), A2 (scorecard chain), A3 (dropped player_stats), B1 (health dedup), B2 (rate-limit wired), B3 (register_cricket_tools), B4 (rule update), C1 (static-seed wiki), C2 (cricsheet URL/drop), C3 (fixtures init).
```

…and update `docs/hot.md` to reflect Phase 2 readiness.
