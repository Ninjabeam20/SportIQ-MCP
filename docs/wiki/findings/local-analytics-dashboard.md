---
title: Local Analytics Dashboard
type: finding
tags: [observability, dashboard, cloud-run, github, pypi, local-tooling]
sources: [scripts/dashboard.py, src/sportiq/core/tool_telemetry.py]
last_updated: 2026-06-16
related: [[project-gcp-deploy]]
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

Cloud Run's `request_count` can't answer "which tool failed / was slow / was
busiest" — every MCP call is HTTP 200 (errors live in the JSON envelope) and the
HTTP layer has no tool name. So `core/tool_telemetry.py` wraps every tool at
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

`core/logging.py` also maps the structlog `level` to Cloud Logging's `severity`
(JSON/prod only) so failed tools surface in Error Reporting. All free: these are
tiny JSON log lines, well under Cloud Logging's free ingest tier — no BigQuery,
Pub/Sub, or OpenTelemetry (the last is on the frozen-stack exclusion list).

## Sources

| Panel | Source | Auth |
| :--- | :--- | :--- |
| Requests/day, latency p50/p99, status split | Cloud Monitoring (`run.googleapis.com/request_count`, `request_latencies`) | GCP ADC |
| Per-tool: calls, error rate, latency, calls-by-client, client-by-tool matrix | Cloud Logging (`jsonPayload.event="tool_call"`) | GCP ADC |
| AI-client breakdown | Cloud Logging (`mcp_request` clientInfo / `userAgent` on `/mcp`) | GCP ADC |
| Stars / forks | GitHub REST `/repos/{repo}` | none (public) |
| Downloads/day | pypistats `/packages/{pkg}/overall` | none |

GitHub daily views/clones are omitted: they require a repo-scoped token. Stars/
forks need none. Add `GITHUB_TOKEN` later to light up the traffic charts.

## Run

```bash
uv sync --extra analytics            # one-time: GCP client libs (dev-only extra)
gcloud auth application-default login # one-time: GCP read access (ADC)
uv run python scripts/dashboard.py   # writes + opens dashboard.html
```

Without the `analytics` extra or ADC, the two GCP panels show `error` and fall
back to cache; GitHub + PyPI still render live. `DASHBOARD_NO_OPEN=1` suppresses
the browser pop (used in CI/headless).

## Not shipped

`google-cloud-monitoring` / `google-cloud-logging` live in the `analytics`
extra, not `dependencies` and not `dev` — PyPI users and CI never pull them.
`.dashboard_cache/` and `dashboard.html` are gitignored.
