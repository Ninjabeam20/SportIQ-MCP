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
- [[cricket-get-live-odds]] — Live bookmaker h2h odds for IPL matches; optional team-name filter.
- [[cricket-find-value-bets]] — +EV "value" bets: de-vigged bookmaker odds vs the heuristic win model (form + H2H + venue).
- [[cricket-head-to-head]] — Head-to-head team comparison using squad form edges + win-probability estimate.
- [[cricket-player-matchup]] — Analyse the head-to-head matchup between two players by role and career stats.

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
- [[f1-qualifying-analysis]] — Analyse a qualifying session: best lap per driver, gap to pole, projected grid.
- [[f1-race-pace-compare]] — Compare race-pace and tyre degradation between two drivers by compound using linear degradation fits.

### Football

- [[football-get-groups]] — Returns the World Cup 2026 group draw (12 groups of 4) and advancement format.
- [[football-get-fixtures]] — Returns WC 2026 fixtures (live providers, else the group schedule).
- [[football-get-standings]] — Returns current WC 2026 group standings.
- [[football-get-squad]] — Returns a national team's WC squad (empty-but-valid via static seed without a key).
- [[football-get-match-stats]] — Returns a team's aggregate WC tournament statistics.
- [[football-get-top-scorers]] — Returns the WC 2026 top scorers.
- [[football-xg-model]] — Expected goals + win/draw/loss probabilities for a matchup (Elo-driven Poisson).
- [[football-match-predictor]] — Most likely scoreline + outcome for a single match.
- [[football-simulate-group]] — Monte Carlo one group into per-team qualification probabilities.
- [[football-simulate-bracket]] — **Phase 4 flagship**: Monte Carlo the full 48-team WC into per-team round + title probabilities.
- [[football-knockout-path]] — Round-by-round survival probabilities for one team.
- [[football-get-odds]] — Live bookmaker h2h odds for WC 2026 matches; optional team-name filter.
- [[football-find-value-bets]] — +EV "value" bets: de-vigged bookmaker odds vs the match model's probabilities (edge %).
- [[football-form-trends]] — Rolling form string, W/D/L record, goals, and xG trajectory for a national team.
- [[football-build-accumulator]] — Accumulator builder: selects top value-bet legs and computes combined odds, combined edge, and risk flag.
- [[cross-sport-accumulator]] — Cross-sport accumulator: combines football + cricket value picks into a single multi-leg acca; one sport failure is non-fatal.

## Models

### Cricket

- [[dream11-scoring]] — T20 fantasy scoring constants + per-component helpers.
- [[dream11-solver]] — Binary ILP picking the optimal 11 + captain + vice-captain.
- [[captain-score]] — `expected_points(player, venue, opp, form)` projection used as solver objective.
- [[form-index]] — 0-100 score blending recent innings with career baseline.
- [[pitch-report]] — Friendliness profile + recommendation derived from a venue record.
- [[cricket-win-probability-model]] — Heuristic pre-match T20 win probability using form (50%), H2H (30%), and venue tilt (20%).
- [[head-to-head]] — `summarise_h2h()` scores squads by player form edges and derives an H2H win-rate estimate.
- [[player-matchup]] — Role-aware heuristic comparing batter avg, bowler avg, and strike rate to assign an edge holder.

### F1

- [[tyre-degradation-model]] — Linear fit (lap_time = intercept + slope × tyre_age) per compound with outlier filtering.
- [[undercut-model]] — Pure-arithmetic undercut viability calculator.
- [[pit-strategy-model]] — Predicts optimal stop laps and compound sequence for the remainder of a race.
- [[race-pace]] — Per-compound linear degradation comparison between two drivers; fresh-tyre intercept delta and overall winner.

### Football

- [[poisson-xg]] — Expected goals -> Poisson scoreline matrix -> P(home/draw/away); shared match engine.
- [[elo]] — Elo win-expectation + rating update; seeds the Poisson engine and the knockout shootout.
- [[group-sim]] — 4-team round-robin Monte Carlo with FIFA tiebreakers; p_advance sums to 2.
- [[bracket-sim]] — Full 48-team tournament Monte Carlo (groups + best-thirds + 32-team knockout).
- [[value-bet]] — De-vig bookmaker odds (multiplicative) and flag outcomes where model_prob beats market by an edge.
- [[parlay-builder]] — `build_accumulator()` pure function: edge filter, dedup, combined odds under independence assumption.

## Chains

### Cricket

- [[cricket-live-score-chain]] — cricapi → ndtv → cricbuzz → rapidapi; 30s TTL.
- [[cricket-scorecard-chain]] — cricapi → rapidapi; 30s TTL; isolated cache key per match_id.
- [[cricket-fixtures-chain]] — cricapi → ndtv → rapidapi; 6h TTL.
- [[cricket-standings-chain]] — cricapi → rapidapi; 10min TTL.
- [[cricket-squad-chain]] — cricapi → static_seed; 12h TTL; always terminates.
- [[cricket-player-stats-chain]] — cricapi_player_info → rapidapi_player_stats; 24h TTL.
- [[cricket-pitch-data-chain]] — static_venue terminator only; 1y TTL (v1 offline-only).
- [[cricket-odds-chain]] — the-odds-api (only source) → stale; 5min fresh / 24h stale TTL.

### F1

- [[f1-sessions-chain]] — openf1 (only source); 6h TTL.
- [[f1-results-chain]] — jolpica (only source); keyed by year + round; 24h TTL.
- [[f1-laps-chain]] — openf1 → fastf1_local; 1h TTL.
- [[f1-stints-chain]] — openf1; 1h TTL.
- [[f1-weather-chain]] — openf1; 10min TTL.
- [[f1-standings-chain]] — jolpica → fastf1_local; 24h TTL.
- [[f1-drivers-chain]] — openf1; 24h TTL.

### Football

- [[football-fixtures-chain]] — api_football → football_data_org → static wc2026; 6h TTL.
- [[football-standings-chain]] — api_football → football_data_org; 10min TTL.
- [[football-groups-chain]] — static wc2026 terminator (draw + Elo ratings); ~1y TTL.
- [[football-team-stats-chain]] — api_football → football_data_org; 24h TTL.
- [[football-squad-chain]] — api_football → static seed; 12h TTL.
- [[football-scorers-chain]] — api_football → football_data_org; 24h TTL.
- [[football-odds-chain]] — the-odds-api (only source) → stale; 5min fresh / 24h stale TTL.

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

### Football

- [[api-football]] — Primary football source; requires APIFOOTBALL_KEY; fixtures, standings, team stats, squads, scorers; 100 req/day.
- [[football-data-org]] — Free fallback (token optional); fixtures, standings, scorers; 10 req/min, 100/day.

### Odds

- [[the-odds-api]] — Live bookmaker h2h odds for IPL + WC 2026; requires THEODDS_KEY; 500 req/month shared.

## Findings

- [[cricapi-envelope-leak]] — CricAPI adapters leaked the request apikey and treated failure responses as empty successes (step8 live pass); fixed via `_unwrap` + `NotFoundError`.
- [[error-envelope-secret-leak]] — Query-param API keys (CricAPI, TheOdds) leaked via the *error* envelope's `sources_tried` (httpx exception URL); fixed with `core/redact.py:scrub` at the fallback capture sites.

## Decisions (ADRs)

- [[0001-fastmcp-over-raw-mcp]] — Why FastMCP decorators instead of the lower-level MCP SDK.
- [[0002-pulp-over-ortools]] — PuLP solver chosen over OR-Tools for Dream11 ILP at 11-player scale.
- [[0003-redis-with-diskcache-fallback]] — Cache backend auto-degrades to diskcache; local dev never assumes Redis.
- [[0004-uvx-distribution]] — Ship via `uvx`; `[project.scripts]` wires `sportiq-mcp = "sportiq.server:main"`.
- [[0005-fallback-chain-pattern]] — Every tool routes through a `FallbackChain[T]`; adapters are pluggable.
- [[0006-respx-for-test-mocking]] — `respx` cassettes only; no live HTTP in CI.
- [[0007-cricket-fallback-strategy]] — Opt-in scrapers + paid escape hatch; CricSheet dropped in Phase 1 cleanup.
- [[0008-football-fallback-strategy]] — Football source ladder + the WC 2026 48-team / 12-group / best-thirds format encoding.
- [[0009-secret-redaction]] — Redact secrets at the fallback capture point (`core/redact.py:scrub`); query-param keys must never reach `sources_tried` or logs.
- [[0010-trusted-publishing]] — PyPI Trusted Publishing via OIDC: no long-lived token, GitHub Actions JWT identity proof, one-time PyPI UI setup required.
