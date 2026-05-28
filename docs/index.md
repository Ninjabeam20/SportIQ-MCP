# sportiq-mcp wiki — index

The entry point Claude reads first. Every wiki page gets one line here, grouped by category, mirroring the page's 1-sentence opener.

## Tools

### Cricket

- [[cricket-get-live-matches]] — Returns all currently live cricket matches across all series.
- [[cricket-get-scorecard]] — Returns the full scorecard for a specific match by match ID.
- [[cricket-get-points-table]] — Returns the points table / standings for a cricket series.
- [[cricket-get-schedule]] — Returns upcoming match schedule, optionally filtered by series.
- [[cricket-get-squad]] — Returns squad roster for a cricket team; always succeeds via static_seed fallback.
- [[cricket-build-dream11-team]] — Phase 2 flagship: optimal Dream11 XI + C/VC via PuLP ILP.
- [[cricket-captain-recommendation]] — Top-3 captain candidates by projected fantasy points.
- [[cricket-differential-picks]] — Low-ownership picks with positive projected upside (ownership estimated).
- [[cricket-player-form-index]] — 0-100 form score derived from player stats chain.
- [[cricket-get-pitch-report]] — Pitch-friendliness summary + recommendation for a venue.

## Models

- [[dream11-scoring]] — T20 fantasy scoring constants + per-component helpers.
- [[dream11-solver]] — Binary ILP picking the optimal 11 + captain + vice-captain.
- [[captain-score]] — `expected_points(player, venue, opp, form)` projection used as solver objective.
- [[form-index]] — 0-100 score blending recent innings with career baseline.
- [[pitch-report]] — Friendliness profile + recommendation derived from a venue record.

## Chains

### Cricket

- [[cricket-live-score-chain]] — cricapi → ndtv → cricbuzz → rapidapi; 30s TTL.
- [[cricket-scorecard-chain]] — cricapi → rapidapi; 30s TTL; isolated cache key per match_id.
- [[cricket-fixtures-chain]] — cricapi → ndtv → rapidapi; 6h TTL.
- [[cricket-standings-chain]] — cricapi → rapidapi; 10min TTL.
- [[cricket-squad-chain]] — cricapi → static_seed; 12h TTL; always terminates.
- [[cricket-player-stats-chain]] — cricapi_player_info → rapidapi_player_stats; 24h TTL.
- [[cricket-pitch-data-chain]] — static_venue terminator only; 1y TTL (v1 offline-only).

## Data sources

### Cricket

- [[cricapi]] — Free JSON API; primary for live, fixtures, standings, squad, player_info; 100 req/day shared.
- [[ndtv-sports-scraper]] — Opt-in scraper (SPORTIQ_ENABLE_NDTV=1); live scores + fixtures.
- [[cricbuzz-scraper]] — Opt-in scraper (SPORTIQ_ENABLE_CRICBUZZ=1); live scores.
- [[rapidapi-cricbuzz]] — Paid licensed Cricbuzz mirror; escape hatch; requires RAPIDAPI_KEY; serves player career stats.
- [[static-seed]] — Local JSON reader; always-on; ships IPL + 4 internationals squads + 14 IPL venues.

## Findings

_(none yet — file via `/project:file-finding` when a chat answer is worth keeping.)_

## Decisions (ADRs)

- [[0001-fastmcp-over-raw-mcp]] — Why FastMCP decorators instead of the lower-level MCP SDK.
- [[0002-pulp-over-ortools]] — PuLP solver chosen over OR-Tools for Dream11 ILP at 11-player scale.
- [[0003-redis-with-diskcache-fallback]] — Cache backend auto-degrades to diskcache; local dev never assumes Redis.
- [[0004-uvx-distribution]] — Ship via `uvx`; `[project.scripts]` wires `sportiq-mcp = "sportiq.server:main"`.
- [[0005-fallback-chain-pattern]] — Every tool routes through a `FallbackChain[T]`; adapters are pluggable.
- [[0006-respx-for-test-mocking]] — `respx` cassettes only; no live HTTP in CI.
- [[0007-cricket-fallback-strategy]] — Opt-in scrapers + paid escape hatch; CricSheet dropped in Phase 1 cleanup.
