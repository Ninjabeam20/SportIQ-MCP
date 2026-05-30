# Step9 Test Matrix — 2026-05-30

State: 36 tools, 291 tests. Gaps identified here are the write-list for this session.

Format: tool | fresh-cache | adapter-success | fallback | stale-serve | all-failed | INVALID_INPUT | NOT_FOUND

Coverage: ✓ = covered, ~ = partial, ✗ = missing, n/a = not applicable to this tool

---

## CRICKET RAW (6 tools)

| Tool | fresh-cache | adapter-success | fallback | stale-serve | all-failed | INVALID_INPUT | NOT_FOUND |
|------|-------------|-----------------|----------|-------------|------------|---------------|-----------|
| cricket_get_live_matches | ✓ | ✓ | ~ | ✓ | ✓ | ✗ | ✗ |
| cricket_get_scorecard | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ |
| cricket_get_points_table | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ |
| cricket_get_schedule | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| cricket_get_squad | ~ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ |
| cricket_get_live_odds | ✗ | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |

Notes:
- cricket_get_squad: static_seed terminator never raises NOT_FOUND — gap is structural, not a bug
- cricket_get_squad: stale-serve untested despite chain support

---

## CRICKET INTEL (5 tools)

| Tool | fresh-cache | adapter-success | fallback | stale-serve | all-failed | INVALID_INPUT | NOT_FOUND |
|------|-------------|-----------------|----------|-------------|------------|---------------|-----------|
| cricket_build_dream11_team | ~ | ✓ | ~ | ✗ | ✓ | ✓ | ✗ |
| cricket_captain_recommendation | ~ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| cricket_differential_picks | ~ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| cricket_player_form_index | ~ | ✓ | ✗ | ✗ | ✓ | ✓ | ✗ |
| cricket_get_pitch_report | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |

---

## F1 RAW (6 tools)

| Tool | fresh-cache | adapter-success | fallback | stale-serve | all-failed | INVALID_INPUT | NOT_FOUND |
|------|-------------|-----------------|----------|-------------|------------|---------------|-----------|
| f1_get_sessions | ~ | ✓ | ✗ | ✗ | ✓ | ✓ | n/a |
| f1_get_drivers | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | n/a |
| f1_get_lap_times | ~ | ✓ | ✗ | ✗ | ✗ | ✗ | n/a |
| f1_get_standings | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | n/a |
| f1_get_race_results | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | n/a |
| f1_get_weather | ~ | ✓ | ✗ | ✗ | ✗ | ✗ | n/a |

Notes:
- f1_get_drivers: UNTESTED — zero coverage across all columns
- f1_get_standings: UNTESTED — zero coverage across all columns

---

## F1 INTEL (5 tools)

| Tool | fresh-cache | adapter-success | fallback | stale-serve | all-failed | INVALID_INPUT | NOT_FOUND |
|------|-------------|-----------------|----------|-------------|------------|---------------|-----------|
| f1_tyre_degradation | ~ | ✓ | ✗ | ✗ | ✓ | ✓ | n/a |
| f1_undercut_window | ~ | ✓ | ✗ | ✗ | ✗ | ✓ | n/a |
| f1_head_to_head_pace | ~ | ✓ | ✗ | ✗ | ✓ | ✗ | n/a |
| f1_weather_strategy_impact | ~ | ✓ | ✗ | ✗ | ✗ | ✗ | n/a |
| f1_predict_pit_strategy | ~ | ✓ | ✗ | ✗ | ✓ | ✗ | n/a |

---

## FOOTBALL RAW (7 tools)

| Tool | fresh-cache | adapter-success | fallback | stale-serve | all-failed | INVALID_INPUT | NOT_FOUND |
|------|-------------|-----------------|----------|-------------|------------|---------------|-----------|
| football_get_groups | ~ | ✓ | ✗ | ✗ | ✗ | n/a | n/a |
| football_get_fixtures | ~ | ✗ | ✗ | ✗ | ✓ | n/a | n/a |
| football_get_standings | ~ | ✗ | ✗ | ✓ | ✗ | n/a | n/a |
| football_get_squad | ~ | ✓ | ✓ | ✗ | ✗ | ✓ | ✗ |
| football_get_match_stats | ~ | ✗ | ✗ | ✗ | ✓ | ✓ | n/a |
| football_get_top_scorers | ✗ | ✗ | ✗ | ✗ | ✗ | n/a | n/a |
| football_get_odds | ~ | ✓ | ✗ | ✗ | ✓ | n/a | n/a |

Notes:
- football_get_top_scorers: UNTESTED — zero coverage across all columns
- football_get_squad: static_seed terminator never raises NOT_FOUND — same structural gap as cricket_get_squad

---

## FOOTBALL INTEL (6 tools)

| Tool | fresh-cache | adapter-success | fallback | stale-serve | all-failed | INVALID_INPUT | NOT_FOUND |
|------|-------------|-----------------|----------|-------------|------------|---------------|-----------|
| football_xg_model | ~ | ✓ | ✗ | ✗ | ✗ | n/a | ✓ |
| football_match_predictor | ~ | ✓ | ✗ | ✗ | ✗ | n/a | ✗ |
| football_simulate_group | ~ | ✓ | ✗ | ✗ | ✗ | n/a | ✓ |
| football_simulate_bracket | ~ | ✓ | ✗ | ✗ | ✗ | n/a | ✗ |
| football_knockout_path | ~ | ✓ | ✗ | ✗ | ✗ | n/a | ✗ |
| football_find_value_bets | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | n/a |

Notes:
- football_find_value_bets: gold standard — all applicable columns covered; use as template

---

## HEALTH (1 tool)

| Tool | fresh-cache | adapter-success | fallback | stale-serve | all-failed | INVALID_INPUT | NOT_FOUND |
|------|-------------|-----------------|----------|-------------|------------|---------------|-----------|
| sportiq_health | ✗ | ✗ | ✗ | ✗ | ✗ | n/a | n/a |

Notes:
- sportiq_health: UNTESTED — zero coverage; health tool deserves at minimum a smoke test

---

## C1 Bracket Seeding (_build_r32)

| Test | Status |
|------|--------|
| wc2026_bracket.json structural data (r32_has_sixteen_matches) | ✓ |
| bracket_order is 16 R32 matches | ✓ |
| third_allocation has 495 bijective rows | ✓ |
| no R32 match pairs same-group winner + runner | ✓ |
| _build_r32 runtime: 32 distinct teams, no intra-group R32 pair | ✗ MISSING |

---

## Gaps → Write-List

### Priority 1 — Completely untested tools (zero coverage)
1. `f1_get_drivers` — add adapter-success + all-failed + INVALID_INPUT
2. `f1_get_standings` — add adapter-success + all-failed + INVALID_INPUT
3. `football_get_top_scorers` — add adapter-success + all-failed
4. `sportiq_health` — smoke test: returns envelope, lists all adapters

### Priority 2 — C1 bracket runtime property test
5. `_build_r32` runtime: 32 distinct teams, no intra-group R32 pair (see tests/unit/test_bracket_data.py)

### Priority 3 — Missing all-failed / stale-serve on mid-coverage tools
6. `cricket_get_scorecard` — all-failed + stale-serve + fallback
7. `cricket_get_points_table` — all-failed + stale-serve + fallback
8. `cricket_get_schedule` — full coverage pass (fresh-cache, fallback, stale, all-failed, INVALID_INPUT)
9. `cricket_get_live_odds` — fresh-cache + fallback + stale-serve
10. `cricket_captain_recommendation` — all-failed + INVALID_INPUT
11. `cricket_differential_picks` — all-failed + INVALID_INPUT
12. `cricket_get_pitch_report` — all-failed
13. `f1_get_lap_times` — all-failed + INVALID_INPUT
14. `f1_get_weather` — all-failed + INVALID_INPUT
15. `f1_undercut_window` — all-failed
16. `f1_weather_strategy_impact` — all-failed + INVALID_INPUT
17. `football_get_groups` — all-failed
18. `football_get_fixtures` — adapter-success + stale-serve
19. `football_get_standings` — adapter-success + all-failed
20. `football_match_predictor` — all-failed + NOT_FOUND
21. `football_simulate_bracket` — all-failed + NOT_FOUND
22. `football_knockout_path` — all-failed + NOT_FOUND

### Priority 4 — Fallback path coverage (chain-level, affects most tools)
- Most tools show ✗ on fallback column. A shared chain-stub test covering the fallback walk
  would close the majority of these in one pass.
