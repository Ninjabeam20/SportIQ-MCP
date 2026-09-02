---
title: Local Analytics Dashboard
type: finding
tags: [observability, dashboard, cloud-run, github, pypi, local-tooling]
sources: [scripts/dashboard.py, src/sportiq/core/tool_telemetry.py]
last_updated: 2026-09-02
related: [[product-hosting-arc]], [[home-server-cutover]]
---

# Local Analytics Dashboard

A read-only, local-only aggregator (`scripts/dashboard.py`) that pulls aggregate
usage into one static `dashboard.html` (Chart.js via CDN). No hosting, no server,
no cost — run on demand and open in the browser.

## Why it looks the way it does

- **Anonymous by design.** The MCP server is keyless (BYO-keys, no auth), so
  there is no per-user identity to report. Every metric is aggregate: request
  counts, latency, coarse AI-client guesses. "Who is using it" can only ever be
  counts + client-type, never named users. The dashboard says so in its header.
- **AI-client breakdown prefers clean names.** `ClientInfoMiddleware` emits an
  `mcp_request` event carrying `clientInfo.name`; the dashboard uses it when
  present and falls back to a `httpRequest.userAgent` heuristic otherwise. Many
  MCP clients connect through generic HTTP libraries, so the `other` /
  `python-httpx` buckets still appear for unidentified clients.
- **Degrade, don't crash** (mirrors the FallbackChain philosophy). Each collector
  is wrapped: on any failure it serves the last value from
  `.dashboard_cache/{source}.json`, and the rest of the dashboard still renders.

## Per-tool telemetry (the goods *and* the bads)

HTTP `request_count` (historically Cloud Run Monitoring) can't answer "which
tool failed / was slow / was busiest" — every MCP call is HTTP 200 (errors live
in the JSON envelope) and the HTTP layer has no tool name. So
`core/tool_telemetry.py` wraps every tool at
startup (`instrument_tools`, same registry walk as `apply_param_descriptions`)
and emits one structured `tool_call` event per call:

```json
{"event":"tool_call","tool":"football_simulate_bracket","success":true,
 "outcome":"ok","latency_ms":1234.5,"source":"openfootball","is_stale":false,
 "client_name":"claude","user_agent":"..."}
```

`client_name`/`user_agent` ride along from `ClientInfoMiddleware`, which binds
them to structlog contextvars per request (and keeps a bounded `session_id →
clientInfo.name` map, since the clean name arrives only at `initialize`). From
these lines the dashboard builds: calls by tool, error rate by tool (+ error
codes), latency by tool (avg/p99), calls by client, the client-by-tool matrix,
and ok-vs-failed over time. `outcome` is `ok` | `error` (envelope) | `exception`.

Live per-tool rows on the Dell come from `SPORTIQ_ANALYTICS_JSONL` (Compose
volume). `core/logging.py` still maps structlog `level` to Cloud Logging
`severity` for historical GCP log lines; after project shutdown those collectors
are archive-only. No BigQuery, Pub/Sub, or OpenTelemetry (frozen-stack exclusion).

## Sources

| Panel | Source | Auth |
| :--- | :--- | :--- |
| Per-tool: calls, error rate, latency, calls-by-client, client-by-tool matrix | Dell JSONL (`SPORTIQ_ANALYTICS_JSONL`) | SSH pull (`scripts/pull_home_analytics.sh`) |
| Requests/day, latency, status split (archive) | Cloud Monitoring cache (project deleted 2026-09-02) | GCP ADC (fails; uses `.dashboard_cache/`) |
| Historical per-tool / AI-client (archive) | Cloud Logging cache | GCP ADC (fails; uses `.dashboard_cache/`) |
| Stars / forks | GitHub REST `/repos/{repo}` | none (public) |
| Downloads/day | pypistats `/packages/{pkg}/overall` | none |

GitHub views/clones need a repo-scoped token. Sponsors GraphQL needs
`read:user`. `scripts/dashboard.py` reads `GITHUB_TOKEN` from the environment,
then repo `.env`, then `gh auth token`. A `gh` login that is only
`gist/read:org/repo` cannot list sponsors.

## Run

```bash
uv sync --extra dev --extra analytics
bash scripts/pull_home_analytics.sh
uv run python scripts/dashboard.py
```

Repo `.env` `GITHUB_TOKEN` is picked up automatically. Dell Compose writes
`SPORTIQ_ANALYTICS_JSONL` to volume `sportiq-analytics`. Pull with
`bash scripts/pull_home_analytics.sh` then re-run the dashboard.

GCP Cloud Logging / Monitoring collectors will fail after project shutdown and
fall back to `.dashboard_cache/` (the 2026-09-02 archive). GitHub + PyPI + Dell
JSONL still render live. `DASHBOARD_NO_OPEN=1` suppresses the browser pop
(used in CI/headless).

## Not shipped

`google-cloud-monitoring` / `google-cloud-logging` live in the `analytics`
extra, not `dependencies` and not `dev` — PyPI users and CI never pull them.
`.dashboard_cache/` and `dashboard.html` are gitignored.
