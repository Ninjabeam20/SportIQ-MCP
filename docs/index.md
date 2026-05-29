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

### F1

- [[f1-get-sessions]] — Returns F1 sessions for a given year, optionally filtered by country.
- [[f1-get-drivers]] — Returns the driver list for a given F1 session.
- [[f1-get-lap-times]] — Returns per-driver lap times for a session (compound lives on stints, not laps).
- [[f1-get-standings]] — Returns driver and constructor championship standings for a given F1 season.
- [[f1-get-race-results]] — Returns the final classification (finishing order, times, points) for one race, keyed by year + round.
- [[f1-get-weather]] — Returns track weather data (temperature, rainfall, wind speed) for a session.
- [[f1-tyre-degradation]] — Fits a linear tyre-degradation model per compound for a driver in a session.
- [[f1-undercut-window]] — Determines if an undercut is viable for the attacker vs a target driver.
- [[f1-head-to-head-pace]] — Compares median lap-time pace between two drivers in the same session.
- [[f1-weather-strategy-impact]] — Analyzes session weather and returns a compound recommendation.
- [[f1-predict-pit-strategy]] — **Phase 3 flagship**: predict optimal pit stops + compound sequence using tyre-degradation fits.

## Models

### Cricket

- [[dream11-scoring]] — T20 fantasy scoring constants + per-component helpers.
- [[dream11-solver]] — Binary ILP picking the optimal 11 + captain + vice-captain.
- [[captain-score]] — `expected_points(player, venue, opp, form)` projection used as solver objective.
- [[form-index]] — 0-100 score blending recent innings with career baseline.
- [[pitch-report]] — Friendliness profile + recommendation derived from a venue record.

### F1

- [[tyre-degradation-model]] — Linear fit (lap_time = intercept + slope × tyre_age) per compound with outlier filtering.
- [[undercut-model]] — Pure-arithmetic undercut viability calculator.
- [[pit-strategy-model]] — Predicts optimal stop laps and compound sequence for the remainder of a race.

## Chains

### Cricket

- [[cricket-live-score-chain]] — cricapi → ndtv → cricbuzz → rapidapi; 30s TTL.
- [[cricket-scorecard-chain]] — cricapi → rapidapi; 30s TTL; isolated cache key per match_id.
- [[cricket-fixtures-chain]] — cricapi → ndtv → rapidapi; 6h TTL.
- [[cricket-standings-chain]] — cricapi → rapidapi; 10min TTL.
- [[cricket-squad-chain]] — cricapi → static_seed; 12h TTL; always terminates.
- [[cricket-player-stats-chain]] — cricapi_player_info → rapidapi_player_stats; 24h TTL.
- [[cricket-pitch-data-chain]] — static_venue terminator only; 1y TTL (v1 offline-only).

### F1

- [[f1-sessions-chain]] — openf1 (only source); 6h TTL.
- [[f1-results-chain]] — jolpica (only source); keyed by year + round; 24h TTL.
- [[f1-laps-chain]] — openf1 → fastf1_local; 1h TTL.
- [[f1-stints-chain]] — openf1; 1h TTL.
- [[f1-weather-chain]] — openf1; 10min TTL.
- [[f1-standings-chain]] — jolpica → fastf1_local; 24h TTL.
- [[f1-drivers-chain]] — openf1; 24h TTL.

## Data sources

### Cricket

- [[cricapi]] — Free JSON API; primary for live, fixtures, standings, squad, player_info; 100 req/day shared.
- [[ndtv-sports-scraper]] — Opt-in scraper (SPORTIQ_ENABLE_NDTV=1); live scores + fixtures.
- [[cricbuzz-scraper]] — Opt-in scraper (SPORTIQ_ENABLE_CRICBUZZ=1); live scores.
- [[rapidapi-cricbuzz]] — Paid licensed Cricbuzz mirror; escape hatch; requires RAPIDAPI_KEY; serves player career stats.
- [[static-seed]] — Local JSON reader; always-on; ships IPL + 4 internationals squads + 14 IPL venues.

### F1

- [[openf1]] — Free public F1 telemetry API; no credentials; endpoints: sessions, drivers, laps, stints, weather.
- [[jolpica]] — Free public Ergast successor; no credentials; historical standings and race results.
- [[fastf1]] — Optional Python library for offline F1 data; lazy-imported; install with `pip install sportiq-mcp[f1]`.

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
