# Phase 2 — Cricket INTEL: flagship #1 (`cricket_build_dream11_team`)

This is the first thing to read on restart for Phase 2. Mirrors the structure of `docs/raw/2026-05-27-phase-1-cleanup.md` (Step 1, Step 2, … with files + tests + verification). Move to `docs/raw/YYYY-MM-DD-phase-2.md` on completion.

## Phase 1 alignment status (verified at plan-write time)

| Target (plan.md §9 Phase 1) | Current state | Delta — explanation |
| :--- | :--- | :--- |
| 6 adapters (incl. `cricsheet`) | 5 adapters (no cricsheet) | ✔ Cleanup C2 — cricsheet endpoint 404 + CSV schema has no `teams` column. ADR-0007 amended. |
| 5 chains (live_score, fixtures, standings, squad, player_stats) | 5 chains but with **scorecard** instead of player_stats | ✔ Cleanup A2/A3 — scorecard pulled into its own chain (per-match cache key); player_stats deferred to Phase 2 with cricapi+rapidapi. |
| `tests/fixtures/__init__.py` shipped | Removed | ✔ Cleanup C3 — directory holds JSON/HTML, not Python. |
| No per-adapter Budget | All cricapi adapters share `Budget(per_day=100)`; chain enforces | ✔ Cleanup B2 — `.claude/rules/api-budgets.md` enforcement now real. |
| Tools registered via decorator-at-import (`from sportiq.server import mcp`) | Tools registered via `register_cricket_tools(mcp)` from `server.py` | ✔ Cleanup B3 — partial-module import hack gone. |
| Caching key spec was hash(args) | Caching key spec is readable colon-joined (current chains already match) | ✔ Cleanup B4 — `.claude/rules/caching-policy.md` updated. |
| Wiki has `cricsheet.md`, `cricket-player-stats-chain.md` | Removed | Will return in Phase 2 with new content. |
| Wiki has `static-seed.md` (no source page existed) | Added | ✔ Cleanup C1 — destination for `[[static-seed]]` backlinks. |

60 tests green at the start of Phase 2 (was 56 pre-cleanup). One commit ahead of any remote: `9a37236 chore: Phase 1 alignment cleanup (A1–C3)`. **NOT pushed** — first task of Phase 2 is the push (Step 0).

---

## Goal

`cricket_build_dream11_team(match_id, strategy="balanced")` returns a valid 11 on a real IPL fixture: ≤100 credits, ≤7 from one team, role mix (1 WK, 3–5 BAT, 1–3 ALL, 3–5 BOWL), C ≠ VC, both in the 11, projected points maximised.

Scope: **core 5 INTEL tools** —

1. `cricket_build_dream11_team` (flagship).
2. `cricket_captain_recommendation`.
3. `cricket_differential_picks`.
4. `cricket_player_form_index`.
5. `cricket_get_pitch_report`.

`cricket_head_to_head` and `cricket_team_news` are deferred to a Phase 2.1 follow-up — they need data sources we don't have yet (scorecard history index; cricket news adapter).

---

## Step 0 — Phase 1 leftovers

0.1 **Push `9a37236` to `origin/main`.** First confirm with the user. Then:

```bash
git remote add origin https://github.com/Ninjabeam20/sportiq-mcp.git
git push -u origin main
```

Repo exists (`gh repo view Ninjabeam20/sportiq-mcp` succeeded). HTTPS is the default (SSH host key isn't trusted yet — `ssh-keyscan github.com >> ~/.ssh/known_hosts` would be the SSH path if preferred).

0.2 **Squad chain shape normalisation.** Add `_normalise_squad(payload, source) -> dict` either inline in each squad adapter or in `cricket/adapters/_normalize.py`. Output shape: `{"players": [{"name": str, "role": "BAT|BOWL|ALL|WK-BAT", "credits": float, "team": str}], "team": str, "source": str}`. The dream11 solver assumes this shape regardless of source.

0.3 **Expand `squads.json` (optional this phase)** to add ≥4 international squads (`IND`, `AUS`, `ENG`, `NZ`) for fixtures outside IPL. If skipped, document in `cricket-get-squad.md` that international squads fall through to CricAPI only.

0.4 **Optional ruff sweep.** 8 pre-existing findings in files cleanup didn't touch — fold in if touching the same files during Phase 2.

0.5 **`.mcp.json` — DO NOT wire the 3 RapidAPI Hub MCP servers in this phase.** Captured in `memory/project-mcp-servers-pending.md`. Phase 3 (F1) or Phase 4 (football) is the right home depending on host.

---

## Step 1 — Dream11 scoring constants + skill page

**Bug/Goal:** Centralise the T20 fantasy scoring table so all models reference one source of truth.

**Files:**

- `src/sportiq/cricket/data/scoring.py` (new) — frozen dataclass `T20Scoring` with: `run = 1`, `boundary_bonus = 1`, `six_bonus = 2`, `half_century_bonus = 4`, `century_bonus = 8`, `duck_penalty = -2` (BAT/ALL/WK only), `wicket = 25`, `lbw_bowled_bonus = 8`, `three_wicket_bonus = 4`, `four_wicket_bonus = 8`, `five_wicket_bonus = 16`, `maiden = 12`, `catch = 8`, `three_catch_bonus = 4`, `stumping = 12`, `run_out_direct = 12`, `run_out_indirect = 6`, `sr_bucket_bonuses` (above 170 = +6, 150.01–170 = +4, 130–150 = +2, 60–70 = -2, 50–59.99 = -4, <50 = -6), `economy_bucket_bonuses` (≤5 = +6, 5.01–6 = +4, 6.01–7 = +2, 10–11 = -2, 11.01–12 = -4, >12 = -6), `captain_multiplier = 2.0`, `vice_captain_multiplier = 1.5`.
- `.claude/skills/dream11-scoring/SKILL.md` (new) — full table + ILP formulation reference.
- `docs/wiki/models/dream11-scoring.md` (new) — wiki version of the skill.
- `tests/unit/test_dream11_scoring.py` (new) — assert each constant against a hand-checked sample over (e.g., "Kohli 72(51) with 6×4 4×6, not out → 72 + 6 + 8 + 4 + 4 = 94 points" — verify the math).

**Verify:** `uv run pytest tests/unit/test_dream11_scoring.py` green.

---

## Step 2 — Player stats — dual-source acquisition

**Goal:** Source player career stats from CricAPI (primary, budgeted) + RapidAPI Cricbuzz (paid escape hatch). Replaces the dropped CricSheet path.

**Files:**

- `src/sportiq/cricket/adapters/cricapi.py` (modify) — add `CricAPIPlayerInfoAdapter` (`/v1/players_info`, fetches by `player_id`) and `CricAPIPlayerSearchAdapter` (`/v1/players`, fetches by name). Both use shared `_CRICAPI_BUDGET`.
- `src/sportiq/cricket/adapters/rapidapi_cricbuzz.py` (modify) — add `RapidAPICricbuzzPlayerStatsAdapter` (`/stats/v1/player/{player_id}/career`). `budget = None`.
- `src/sportiq/cricket/chains.py` (modify) — add `player_stats_chain: [_cricapi_player_info, _rapidapi_player_stats]`, `cache_key_fn` lambda `player_id, **_: f"sportiq:cricket:player_stats:{player_id}"`, `fresh_ttl=86400`, `stale_ttl=604800`. Register both adapters for health (dedupe by name will keep first).
- `tests/fixtures/cricapi/players_info.json` (new) — synthetic real-shape sample.
- `tests/fixtures/rapidapi/player_career.json` (new) — synthetic real-shape sample.
- `tests/adapters/test_cricapi.py` (modify) — adapter test for `player_info`.
- `tests/adapters/test_rapidapi_cricbuzz.py` (modify) — adapter test for `player_stats`.
- `tests/chains/test_cricket_chains.py` (modify) — `test_player_stats_chain_keys_by_player_id` + `test_player_stats_chain_falls_through`.
- `docs/wiki/chains/cricket-player-stats-chain.md` (NEW — recreates the file deleted in cleanup A3, with new content).
- `docs/wiki/data-sources/cricapi.md` (modify) — add `players_info` row.
- `docs/wiki/data-sources/rapidapi-cricbuzz.md` (modify) — add `stats/v1/player/{id}/career` row.
- `docs/index.md` (modify) — add `[[cricket-player-stats-chain]]` row.

**Verify:** Chain test + adapter tests green; chain hits cricapi first, falls to rapidapi on cricapi failure.

---

## Step 3 — form_index model

**Goal:** Given a player + last N=5 scorecards + career baseline, return a 0–100 form score.

**Files:**

- `src/sportiq/cricket/models/__init__.py` (new).
- `src/sportiq/cricket/models/form_index.py` (new) — pure function `compute_form_index(recent_innings: list[dict], career_avg: float, career_sr: float) -> dict`. Weights last 5 innings more than career; output `{form_score: 0–100, trend: "rising|stable|falling", samples: N}`.
- `tests/unit/test_form_index.py` (new) — synthetic inputs: declining → low; explosive → high; missing recent → fallback to career mean.

**Verify:** `uv run pytest tests/unit/test_form_index.py` green; output bounded 0–100.

---

## Step 4 — captain_score model

**Goal:** Given a candidate + venue + opposition + recent form, return expected fantasy points (used by both `build_dream11_team` and `captain_recommendation`).

**Files:**

- `src/sportiq/cricket/models/captain_score.py` (new) — pure function `expected_points(player, venue, opposition_strength, form_score) -> float`. Uses `T20Scoring` constants. Probabilistic projection: `E[runs] * run_constant + E[boundaries] * boundary_bonus + ...`.
- `tests/unit/test_captain_score.py` (new) — synthetic player/venue/opposition inputs; assert relative ordering (higher form → higher score).

**Verify:** `uv run pytest tests/unit/test_captain_score.py` green; monotonic in `form_score`.

---

## Step 5 — pitch_report model + venues seed

**Goal:** Static venue characteristics + optional recent-match enrichment.

**Files:**

- `src/sportiq/cricket/data/venues.json` (new) — hand-seeded for ~14 IPL venues with `{name, city, pitch_type ("batting"|"bowling"|"balanced"), avg_first_innings, avg_chasing, boundary_size_m}`.
- `src/sportiq/cricket/adapters/static_seed.py` (modify) — add `StaticSeedVenueAdapter` class (one class per data file, mirroring `StaticSeedSquadAdapter`).
- `src/sportiq/cricket/chains.py` (modify) — add `pitch_data_chain: [_static_venue]` (only the terminator for v1). Cache key `f"sportiq:cricket:pitch:{venue_id}"`, `fresh_ttl=∞` effectively (use `31_536_000` = 1y), `stale_ttl=0`.
- `src/sportiq/cricket/models/pitch_report.py` (new) — combines `venues.json` + (optional) recent-match scorecards at venue → `{batting_friendly: 0–1, expected_first_inn: int, recommendation: str}`.
- `tests/adapters/test_static_seed.py` (modify) — venue lookup test.
- `tests/unit/test_pitch_report.py` (new).
- `docs/wiki/chains/cricket-pitch-data-chain.md` (new).
- `docs/wiki/data-sources/static-seed.md` (modify) — mention `venues.json`.
- `docs/index.md` (modify) — add `[[cricket-pitch-data-chain]]`.

**Verify:** `pitch_report(venue="Wankhede")` returns batting-friendly profile; `pitch_report(venue="Chennai")` returns spinning profile.

---

## Step 6 — dream11_solver (PuLP ILP)

**Goal:** Pure function returning a valid 11 + C/VC under Dream11 constraints.

**Files:**

- `src/sportiq/cricket/models/dream11_solver.py` (new). Function `solve(candidates: list[dict], strategy: str = "balanced") -> dict`. Each candidate is `{name, role, credits, projected_points, team}`. Output `{players: list[11], captain, vice_captain, total_credits, total_projected_points}`.
- Constraints (`PuLP LpProblem` with `LpBinary` vars per player + per captain + per vc):
  - `sum(x_i) == 11`.
  - `sum(credits_i * x_i) <= 100`.
  - `sum(x_i for i in team_A) <= 7` and same for `team_B`.
  - `1 <= sum(x_i for role==WK) <= 4`.
  - `3 <= sum(x_i for role==BAT) <= 5` (config-tunable via `strategy`).
  - `1 <= sum(x_i for role==ALL) <= 3`.
  - `3 <= sum(x_i for role==BOWL) <= 5`.
  - `sum(c_i) == 1`, `sum(vc_i) == 1`, `c_i + vc_i <= 1` (no overlap), `c_i <= x_i`, `vc_i <= x_i`.
- Objective: maximise `sum(projected_points_i * x_i + projected_points_i * c_i * 1.0 + projected_points_i * vc_i * 0.5)` — i.e., captain gets 1× extra on top of the base (effective ×2), VC gets 0.5× extra (effective ×1.5).
- `tests/unit/test_dream11_solver.py` (new) — one test per constraint (over-credit, over-team-cap, missing WK, infeasibility raises `InvalidInputError`), one end-to-end with a 22-candidate synthetic pool.

**Verify:** `uv run pytest tests/unit/test_dream11_solver.py` green; solver returns optimal on the synthetic pool in <500ms.

---

## Step 7 — 5 INTEL tools + chain wiring

**Goal:** Expose the models as MCP tools through `register_cricket_tools(mcp)` (already in place from cleanup B3).

**Files:**

- `src/sportiq/cricket/tools.py` (modify) — add 5 new tools. If the file exceeds ~250 LOC, split into `cricket/intel_tools.py` and import in the registrar.
  - `cricket_build_dream11_team(match_id: str, strategy: str = "balanced") -> dict`. Internally: fetch squads of both teams via `squad_chain`, fetch player_stats via `player_stats_chain`, fetch pitch via `pitch_data_chain`, compute `expected_points` per candidate, call `dream11_solver.solve()`, return envelope.
  - `cricket_captain_recommendation(match_id: str) -> dict`. Top-3 captain candidates by `expected_points`.
  - `cricket_differential_picks(match_id: str, ownership_threshold: int = 20) -> dict`. Top picks with `meta.estimated: true` for ownership (per plan.md §10 #7).
  - `cricket_player_form_index(player_id: str) -> dict`. Wraps `form_index` model + `player_stats_chain` recent + career.
  - `cricket_get_pitch_report(venue_or_match_id: str) -> dict`. Wraps `pitch_report` model.
- `src/sportiq/cricket/tools.py` (modify) — extend `register_cricket_tools(mcp)` to register all 10 cricket tools (5 RAW + 5 INTEL).
- `tests/tools/test_cricket_intel_tools.py` (new) — end-to-end stubs: chain output mocked, assert envelope shape, `meta.estimated` for differentials, error envelope on `AllSourcesFailedError`.

**Verify:** `npx @modelcontextprotocol/inspector uvx --from . sportiq-mcp` lists all 11 tools (5 RAW cricket + 5 INTEL cricket + `sportiq_health`).

---

## Step 8 — Docs (wiki + index + log + hot)

**Files added:**

- `docs/wiki/tools/cricket-build-dream11-team.md`
- `docs/wiki/tools/cricket-captain-recommendation.md`
- `docs/wiki/tools/cricket-differential-picks.md`
- `docs/wiki/tools/cricket-player-form-index.md`
- `docs/wiki/tools/cricket-get-pitch-report.md`
- `docs/wiki/models/dream11-scoring.md` (Step 1)
- `docs/wiki/models/form-index.md` (Step 3)
- `docs/wiki/models/captain-score.md` (Step 4)
- `docs/wiki/models/pitch-report.md` (Step 5)
- `docs/wiki/models/dream11-solver.md` (Step 6)
- `docs/wiki/chains/cricket-player-stats-chain.md` (Step 2)
- `docs/wiki/chains/cricket-pitch-data-chain.md` (Step 5)

**Files modified:**

- `docs/index.md` — add 5 INTEL tools, 5 models, 2 chains, players_info data source row updates.
- `docs/wiki/data-sources/static-seed.md` — mention `venues.json`.
- `docs/wiki/data-sources/cricapi.md` — add `players_info` endpoint row.
- `docs/wiki/data-sources/rapidapi-cricbuzz.md` — add player career endpoint row.
- `docs/hot.md` — "Phase 2 shipped — Dream11 ILP flagship live".
- `docs/log.md` — append `## [YYYY-MM-DD] phase-complete | Phase 2 — Cricket INTEL flagship #1 ...`.
- `README.md` — Dream11 demo section + GIF placeholder.

---

## Step 9 — Verification

```bash
# 1. Full suite green
uv run pytest

# 2. Schema (all 11 tools registered)
uv run python -c "
import asyncio
from sportiq.server import mcp
async def go():
    tools = await mcp.list_tools()
    names = sorted(t.name for t in tools)
    print('\n'.join(names))
    assert 'cricket_build_dream11_team' in names
asyncio.run(go())
"

# 3. End-to-end (requires CRICAPI_KEY)
uv run python -c "
import asyncio
from sportiq.cricket.tools import cricket_build_dream11_team
async def go():
    r = await cricket_build_dream11_team(match_id='<recent IPL match id>')
    d = r['data']
    assert len(d['players']) == 11
    assert d['total_credits'] <= 100
    teams = {p['team'] for p in d['players']}
    for t in teams:
        assert sum(1 for p in d['players'] if p['team']==t) <= 7
    assert d['captain'] != d['vice_captain']
    print('flagship green')
asyncio.run(go())
"

# 4. Budget smoke
uv run python -c "
import asyncio
from sportiq.core.health import get_health_report
async def go():
    r = await get_health_report()
    print('cricapi quota remaining:', r['data']['quotas'].get('cricapi'))
asyncio.run(go())
"
```

---

## Step 10 — Future RapidAPI MCP servers (saved for later, do NOT wire this phase)

Three RapidAPI Hub MCP servers the user wants registered in `.mcp.json` in a later phase. Captured here so the next session can act without re-asking.

1. **RapidAPI Hub — Sportspage Feeds** (`sportspage-feeds.p.rapidapi.com`). Phase 3 or 4 candidate.
2. **RapidAPI Hub — Football Prediction** (`football-prediction-api.p.rapidapi.com`). Phase 4 candidate (flagship calibration).
3. **RapidAPI Hub — Live Sports Odds** (`odds.p.rapidapi.com`). Phase 4 candidate (pre-match odds + cricket differential ownership proxy).

Connect snippet template (replace `<host>` and supply the operator's `RAPIDAPI_KEY`):

```json
{
  "mcpServers": {
    "RapidAPI Hub - <Name>": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://mcp.rapidapi.com",
        "--header",
        "x-api-host: <host>",
        "--header",
        "x-api-key: <RAPIDAPI_KEY>"
      ]
    }
  }
}
```

Wire into `.mcp.json` at repo root; ADR-it if it changes the cross-server contract.

---

## Open questions (deliberate, called out for the next session)

- **Exact CricAPI player endpoint paths** — `cricketdata.org/code-samples.aspx` returned HTTP 500 during planning. Plan uses `/v1/players_info` and `/v1/players` based on prior cassette conventions and CricAPI's public docs; reconcile against the live response shape on first call in Step 2.
- **Strategy variants** — Phase 2 ships `balanced` only. `aggressive` (top-heavy batting) and `differential` (low-ownership weighted) land post-flagship as soft enums on `strategy`.
- **Ownership % for `cricket_differential_picks`** — no first-class source; Phase 2 estimates with `meta.estimated: true` (plan.md §10 #7). Real ownership lands when [[project-mcp-servers-pending]]'s Live Sports Odds is wired.
- **`squads.json` international coverage** — Step 0.3 is optional. If skipped, `cricket_build_dream11_team` works on IPL fixtures only.

---

## When you finish

Per CLAUDE.md Rule #8:

**Files added:** …
**Files modified:** …
**Intentionally not touched:** …
**Follow-up needed:** …

Then append a single line to `docs/log.md`:

```
## [YYYY-MM-DD] phase-complete | Phase 2 — Cricket INTEL flagship #1
5 INTEL tools (build_dream11_team, captain_recommendation, differential_picks, player_form_index, get_pitch_report), 5 models (dream11_solver, form_index, captain_score, pitch_report + scoring data), 2 new chains (player_stats, pitch_data), 2 new adapter classes per upstream (cricapi player + rapidapi player). N tests (M new).
```

Update `docs/hot.md` to reflect Phase 3 readiness.
