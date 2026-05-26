# sportiq-mcp wiki — index

The entry point Claude reads first. Every wiki page gets one line here, grouped by category, mirroring the page's 1-sentence opener.

## Tools

_(none yet — Phase 1 adds cricket RAW tools.)_

## Models

_(none yet — Phase 2 adds Dream11 scoring + form index.)_

## Chains

_(none yet — Phase 1 adds cricket-live-score chain.)_

## Data sources

_(none yet — Phase 1 adds CricAPI and Cricbuzz scraper.)_

## Findings

_(none yet — file via `/project:file-finding` when a chat answer is worth keeping.)_

## Decisions (ADRs)

- [[0001-fastmcp-over-raw-mcp]] — Why FastMCP decorators instead of the lower-level MCP SDK.
- [[0002-pulp-over-ortools]] — PuLP solver chosen over OR-Tools for Dream11 ILP at 11-player scale.
- [[0003-redis-with-diskcache-fallback]] — Cache backend auto-degrades to diskcache; local dev never assumes Redis.
- [[0004-uvx-distribution]] — Ship via `uvx`; `[project.scripts]` wires `sportiq-mcp = "sportiq.server:main"`.
- [[0005-fallback-chain-pattern]] — Every tool routes through a `FallbackChain[T]`; adapters are pluggable.
- [[0006-respx-for-test-mocking]] — `respx` cassettes only; no live HTTP in CI.
