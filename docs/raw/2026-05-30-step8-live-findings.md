# step8 live testing pass — raw findings (2026-05-30)

Captured by `scripts/live_check.py` against real upstreams. Raw notes, immutable.
Keys present: CRICAPI, APIFOOTBALL, THEODDS, FOOTBALLDATA, RAPIDAPI. Backend: diskcache.

## Pass A — cricket (CricAPI + TheOdds)
- `cricket_get_live_matches` → cricapi, 25 matches. OK.
- `cricket_get_scorecard` → CricAPI returned `{apikey, status:"failure", reason:"ERR: Scorecard <id> not found"}`.
  🔴 **Adapter returned this RAW as success → request apikey leaked into tool data + failure masqueraded as success.**
- `cricket_get_points_table` → same envelope leak (raw passthrough).
- `cricket_get_squad(team="MI")` → 0 players, source=cache. 🟠 **cricapi squad adapter called with series_id=None
  "succeeded" empty and cached it, shadowing the 11-player static seed.**
- `cricket_get_schedule` → cricapi, 25 matches. OK.
- `cricket_get_pitch_report("Wankhede Stadium")` → static_seed, batting_friendly=0.795. OK.
- `cricket_get_live_odds` → theodds, 1 event. OK.
- `cricket_player_form_index` → not exercised (no player_id discovered).
- CricAPI quota after pass: ~95/100. TheOdds: ~15/16.

## Pass B — F1 (OpenF1 + Jolpica, keyless)
- Discovered session_key=7953 (Bahrain 2023 Race), drivers [1,2,4,...].
- sessions/standings/race_results/drivers/lap_times/weather/tyre_degradation/weather_strategy_impact/
  predict_pit_strategy → all OK live.
- `f1_predict_pit_strategy(driver 1)` → total_laps inferred = **57** (Bahrain ✓, validates step7 inference +
  step8 lap_number>0 guard). Strategy: one stop on lap 31, HARD→MEDIUM, confidence 0.95.
- `f1_undercut_window` / `f1_head_to_head_pace` → ALL_SOURCES_FAILED on the FIRST cold-cache run, then OK on
  re-run. 🟡 transient OpenF1 burst hiccup during cold fan-out; self-recovers once laps are cached. Benign.

## Pass A — football (API-Football + TheOdds)
- fixtures / standings / top_scorers → api_football, **0 items**. Expected off-season (WC 2026 starts Jun 2026).
  🟡 verify the adapters scope league/season to WC 2026 (vs a generic empty) — low priority.
- `football_get_squad("ARG")` → static_seed, empty-but-valid (0 players). Known gap → step8 Part 3.2 fills marquee rosters.
- groups / match_predictor / xg_model / simulate_group / knockout_path / simulate_bracket → all OK off static seed.
- `football_get_odds` → theodds, **72 events** live. (Feeds the Part 2 value-bet tool.)
- `football_get_match_stats` → not exercised (needs a numeric team id).

## Pass C — MCP schema
- Server boots; `mcp.list_tools()` → **35 tools**. Every tool has a description; all params typed (no Any/untyped). No drift.

## Triage
- 🔴 CricAPI envelope leak + failure-as-success → FIXED (adapter `_unwrap`, status check, apikey stripped).
- 🟠 squad series_id=None shadows static seed → FIXED (adapter raises NotFoundError without series_id).
- ℹ️ scorecard / points_table ALL_SOURCES_FAILED = CricAPI free-tier limitation (endpoints not on free tier) +
  no paid RapidAPI subscription. Not a code bug; honest envelope.
- 🟡 deferred: F1 cold-burst transient; API-Football off-season league scoping; football marquee squads (Part 3.2).
