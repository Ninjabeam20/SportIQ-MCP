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

HTTP transport enforces a 1 MiB application-level MCP request-body limit before the
request reaches FastMCP. Upstream HTTP responses larger than 10 MiB are rejected, but
that separate check occurs after httpx has buffered the response. Output truncation is
tool-specific rather than a universal response limit; tools that truncate report it
through response metadata.

## Operational telemetry

HTTP mode emits structured application logs containing client software name/version,
User-Agent, tool name, outcome, latency, selected source, and staleness. Cloud Run may
also retain platform network/request metadata according to the operator's logging
configuration. Local stdio mode emits logs locally but sends no telemetry to a
SportIQ-hosted service.

## Hosted deployment (public Cloud Run instance)

The public instance at `https://sportiq-mcp-329580761892.us-central1.run.app/mcp` is an
unauthenticated, read-only data service. A hosted operator may configure provider
credentials, so callers must not assume the host is secret-free; this repository does
not claim the deployment's unverified current key inventory. Application logging
redacts known credential patterns, but provider quota remains an operator concern.

The application accepts at most 60 POST `/mcp` requests per client and 300 total per
minute, returning HTTP 429 with `Retry-After` before MCP dispatch. Client identities are
hashed before entering cache keys. A validated leftmost `X-Forwarded-For` address is
trusted only when Cloud Run's `K_SERVICE` marker is present; other environments use the
ASGI peer address. Initialize-body telemetry capture is capped at 64 KiB, and the five
expensive simulation/strategy/solver tools share a concurrency limit of two.

Rate counters are per process. The hosted policy therefore requires Cloud Run
`--max-instances=1`; increasing that value multiplies the effective global limit and
must be accompanied by a shared admission-control design. These controls are present in
this branch, but this branch did not change or validate the live Cloud Run deployment.

In HTTP transport mode the server disables FastMCP's DNS-rebinding protection
(`enable_dns_rebinding_protection=False` in `server.py`). This is intentional and required:
Cloud Run forwards a real `Host` header that the default `localhost`-only allowlist rejects.
The deployment perimeter (Cloud Run's HTTPS front end) handles transport security; the tools
themselves are read-only and stateless, so there is no rebinding-sensitive surface to protect.
Self-hosters who expose the HTTP endpoint on an untrusted network should put it behind the same
kind of managed HTTPS perimeter.

## Independent review

sportiq-mcp is **fully open source (MIT)** — the entire codebase, build pipeline, and test
suite are public, so anyone can audit it themselves rather than trust a claim. The following
are historical automated reviews, not statements about the current branch:

- **Full MCP-rubric audit (2026-06-04)** — a code-audit agent ran static analysis, a runtime
  smoke test, and a **clean-room install** (fresh venv → install the published wheel → drive the
  server over real MCP stdio). Verdict: **ship-ready, no P0 (broken / data-wrong / security)
  findings**. The build artifact was verified to exclude `.env`, internal docs, and test
  fixtures — **no secret leak**. `ruff` clean, full test suite green.
- **Pre-launch multi-agent sweep (2026-06-06)** — three independent read-only agents (secret
  forensics, code review, infra/packaging). Secret-forensics verdict: **CLEAN** — no credential
  was ever present in the git history, branches, or working tree; `.env` was never committed;
  recorded test fixtures are scrubbed. Cleared for publish.

These are automated AI reviews, not a formal third-party security certification or penetration
test. Because the project is open source, you're encouraged to re-run your own audit — point any
AI code-review tool at <https://github.com/Ninjabeam20/SportIQ-MCP> and verify the above for
yourself.

## Reporting a vulnerability

For sensitive disclosures, email utkarshgupta885@gmail.com with subject
`[sportiq-mcp] security`. Do not open a public issue for a suspected vulnerability.
