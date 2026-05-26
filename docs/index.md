# sportiq-mcp wiki — index

The entry point Claude reads first. Every wiki page gets one line here, grouped by category, mirroring the page's 1-sentence opener.

## Tools

### Cricket

- [[cricket-get-live-matches]] — Returns all currently live cricket matches across all series.
- [[cricket-get-scorecard]] — Returns the full scorecard for a specific match by match ID.
- [[cricket-get-points-table]] — Returns the points table / standings for a cricket series.
- [[cricket-get-schedule]] — Returns upcoming match schedule, optionally filtered by series.
- [[cricket-get-squad]] — Returns squad roster for a cricket team; always succeeds via static_seed fallback.

## Models

_(none yet — Phase 2 adds Dream11 scoring + form index.)_

## Chains

### Cricket

- [[cricket-live-score-chain]] — cricapi → ndtv → cricbuzz → rapidapi; 30s TTL.
- [[cricket-fixtures-chain]] — cricapi → ndtv → rapidapi; 6h TTL.
- [[cricket-standings-chain]] — cricapi → rapidapi; 10min TTL.
- [[cricket-squad-chain]] — cricapi → cricsheet → static_seed; 12h TTL; always terminates.
- [[cricket-player-stats-chain]] — cricsheet → cricapi; 24h TTL.

## Data sources

### Cricket

- [[cricapi]] — Free JSON API; primary for live, fixtures, standings, squad; 100 req/day.
- [[cricsheet]] — Free public-domain data; always enabled; used for player stats and squad.
- [[ndtv-sports-scraper]] — Opt-in scraper (SPORTIQ_ENABLE_NDTV=1); live scores + fixtures.
- [[cricbuzz-scraper]] — Opt-in scraper (SPORTIQ_ENABLE_CRICBUZZ=1); live scores.
- [[rapidapi-cricbuzz]] — Paid licensed Cricbuzz mirror; escape hatch; requires RAPIDAPI_KEY.

## Findings

_(none yet — file via `/project:file-finding` when a chat answer is worth keeping.)_

## Decisions (ADRs)

- [[0001-fastmcp-over-raw-mcp]] — Why FastMCP decorators instead of the lower-level MCP SDK.
- [[0002-pulp-over-ortools]] — PuLP solver chosen over OR-Tools for Dream11 ILP at 11-player scale.
- [[0003-redis-with-diskcache-fallback]] — Cache backend auto-degrades to diskcache; local dev never assumes Redis.
- [[0004-uvx-distribution]] — Ship via `uvx`; `[project.scripts]` wires `sportiq-mcp = "sportiq.server:main"`.
- [[0005-fallback-chain-pattern]] — Every tool routes through a `FallbackChain[T]`; adapters are pluggable.
- [[0006-respx-for-test-mocking]] — `respx` cassettes only; no live HTTP in CI.
- [[0007-cricket-fallback-strategy]] — Opt-in scrapers + paid escape hatch; CricSheet as free legal primary.
