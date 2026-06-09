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

## Hosted deployment (public Cloud Run instance)

The public instance at `https://sportiq-mcp-329580761892.us-central1.run.app/mcp` runs with
**zero API keys** configured — there are no secrets on the host to leak and no operator quota
to burn. It exposes only the read-only/keyless tool set; live-score and odds tools that require
credentials are inert there. The endpoint is `--allow-unauthenticated` by design (a public,
read-only data service) and scales to zero when idle.

In HTTP transport mode the server disables FastMCP's DNS-rebinding protection
(`enable_dns_rebinding_protection=False` in `server.py`). This is intentional and required:
Cloud Run forwards a real `Host` header that the default `localhost`-only allowlist rejects.
The deployment perimeter (Cloud Run's HTTPS front end) handles transport security; the tools
themselves are read-only and stateless, so there is no rebinding-sensitive surface to protect.
Self-hosters who expose the HTTP endpoint on an untrusted network should put it behind the same
kind of managed HTTPS perimeter.

## Reporting a vulnerability

Open a GitHub issue tagged `security`. For sensitive disclosures, email
utkarshgupta885@gmail.com with subject `[sportiq-mcp] security`.
