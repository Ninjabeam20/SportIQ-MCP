# Security Policy

## Data-flow trust model

sportiq-mcp fetches data from external sports APIs and (when opted in) HTML scrapers,
then passes it to an MCP-connected LLM client. Upstream content is **data**, never
instructions. A hostile upstream could embed prompt-injection payloads in match titles,
player names, or team descriptions — the server does not attempt to sanitise them, so
operators should be aware that model behaviour can be influenced by upstream content.

## API key handling

Keys are read from environment variables / `.env` at startup and are never written to
logs, error envelopes, or cache entries. The redaction layer (`core/redact.py`) scrubs
known key patterns from all structured log events and fallback-attempt records. Keys
that must appear as query parameters (CricAPI, The Odds API) are masked at the capture
point — they are never stored in plain text beyond the process environment.

## Scraper opt-in (ADR-0007)

NDTV Sports and Cricbuzz scrapers are **disabled by default**. They must be explicitly
enabled by the operator via `SPORTIQ_ENABLE_NDTV=1` / `SPORTIQ_ENABLE_CRICBUZZ=1`.
Scrapers are rate-limited to ≤ 1 req/3 s. Operators enabling scrapers accept the ToS
risk of the respective sites.

## Payload size limits

Tools cap list payloads at 200 items and string fields at 500 characters to prevent a
hostile or misbehaving upstream from blowing the LLM context window or server memory.
Truncated responses carry `meta.truncated: true`.

## Reporting a vulnerability

Open a GitHub issue tagged `security`. For sensitive disclosures, email
utkarshgupta885@gmail.com with subject `[sportiq-mcp] security`.
