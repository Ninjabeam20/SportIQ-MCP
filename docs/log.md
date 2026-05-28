# Operation log

Append-only. Grep with `grep "^## \[" docs/log.md`.

Operations: `ingest` · `decision` · `lint` · `release` · `tool-added` · `adapter-added` · `finding-filed` · `cache-cleared` · `phase-complete`.

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
