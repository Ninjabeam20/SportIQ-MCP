# Dev notes

## Running the server

The server speaks two transports. **stdio** is the default (the `uvx` contract, single-client); **streamable-HTTP** is what the Cloud Run deployment runs.

```bash
uv sync --extra dev                      # install everything incl. test/lint deps

# stdio (default) — what an MCP client like Claude Desktop launches
uv run python -m sportiq.server
#   or the packaged entry point:
uv run sportiq-mcp

# streamable-HTTP — mirrors prod; serves the MCP endpoint at http://localhost:8080/mcp
SPORTIQ_TRANSPORT=http PORT=8080 uv run python -m sportiq.server
```

Useful env vars (all optional):

| Var | Default | Effect |
|---|---|---|
| `SPORTIQ_TRANSPORT` | `stdio` | `http`/`streamable-http` to serve over HTTP |
| `PORT` | `8080` | HTTP port (Cloud Run convention) |
| `SPORTIQ_LOG_LEVEL` | `INFO` | structlog filter level |
| `SPORTIQ_LOG_FORMAT` | auto | `json` (prod) / `pretty` (local). Auto = json when `K_SERVICE` is set |
| `SPORTIQ_FOOTBALL_LIVE_ELO` | off | walk the Elo seed forward from completed WC results |
| `SPORTIQ_ENABLE_NDTV` / `SPORTIQ_ENABLE_CRICBUZZ` | off | opt-in scrapers |

API keys (`CRICAPI_KEY`, `APIFOOTBALL_KEY`, `FOOTBALLDATA_KEY`, `THEODDS_KEY`, `RAPIDAPI_KEY`) are read from `.env` or the environment. All are optional — missing keys make those adapters fail their healthcheck and the FallbackChain walks past them to keyless sources / static seeds.

## Calling tools

The practical way to exercise tools by hand is the **MCP Inspector** (a web UI that handles the JSON-RPC handshake for you):

```bash
npx @modelcontextprotocol/inspector uvx --from . sportiq-mcp
#   or the project shortcut:
#   /project:inspect
```

It lists all 44 tools with their schemas; pick one, fill the form, and see the `{data, meta}` / `{error}` envelope.

Against a **running HTTP server**, the handshake is: `POST /mcp` `initialize` → capture the `Mcp-Session-Id` response header → `POST /mcp` `tools/call` echoing that header. The Inspector does this for you; raw `curl` is fiddly because of the session + SSE framing. Quick liveness check:

```bash
curl -s -XPOST http://localhost:8080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
```

`sportiq_health()` is the tool to call first — it surfaces cache backend, per-source budget, and adapter health.

## Observability (what gets logged)

Every tool call emits a structured `tool_call` event (see `src/sportiq/core/tool_telemetry.py`) — this is the signal the analytics dashboard reads. To watch it live locally, run the HTTP server in JSON mode and tail stderr while you call tools through the Inspector:

```bash
SPORTIQ_TRANSPORT=http SPORTIQ_LOG_FORMAT=json uv run python -m sportiq.server
# in another shell, call a tool via the Inspector, then watch for lines like:
# {"event":"tool_call","tool":"football_simulate_bracket","success":true,
#  "outcome":"ok","latency_ms":1234.5,"source":"openfootball","client_name":"...","severity":"INFO"}
```

- `outcome` is `ok` | `error` (returned an error envelope — still HTTP 200) | `exception` (uncaught).
- `client_name` / `user_agent` are attributed by `ClientInfoMiddleware` (HTTP transport only).
- `severity` is mapped from the log level for Cloud Logging / Error Reporting (JSON format only).

In production these land in Cloud Logging as `jsonPayload.event="tool_call"`, which is exactly what the dashboard's `collect_tool_stats()` queries.

## Tests & lint

```bash
uv run --extra dev pytest        # full suite — MUST pass before commit (pytest lives in the dev extra)
uv run --extra dev pytest tests/unit/test_tool_telemetry.py -q   # one file
uv run --extra dev ruff check src/ scripts/                      # lint
```

## Analytics dashboard

Read-only local dashboard that pulls aggregate usage from Cloud Run (request volume + latency), Cloud Logging (per-tool `tool_call` telemetry + AI-client breakdown), GitHub (stars/forks/traffic), and PyPI (download counts). Renders a static `dashboard.html` with Chart.js and opens it in the browser. No server, no hosting, no cost.

> The per-tool panels (calls/errors/latency by tool, client-by-tool matrix) only populate once a build emitting `tool_call` events is **deployed** to Cloud Run — they read those events back out of Cloud Logging. Until then those panels render an empty-state note and everything else still works.

### One-time setup

```bash
uv sync --extra analytics          # installs google-cloud-monitoring + google-cloud-logging
gcloud auth application-default login   # grants read access to Cloud Run / Logging via ADC
```

`GITHUB_TOKEN` is optional. Without it the GitHub panel shows stars/forks/issues but omits the daily views and clones breakdown (those endpoints require push access).

```bash
export GITHUB_TOKEN=ghp_...        # repo-scoped, read-only is enough
```

### Run

```bash
uv run python scripts/dashboard.py
```

Opens `dashboard.html` at the repo root automatically. To suppress auto-open (e.g. in CI):

```bash
DASHBOARD_NO_OPEN=1 uv run python scripts/dashboard.py
```

Each collector degrades independently — if GCP auth is missing or an API is down, that panel falls back to the last cached value in `.dashboard_cache/` and the rest of the dashboard still renders.

### What it shows

| Panel | Source | Notes |
|---|---|---|
| Requests / day (stacked by 2xx/4xx/5xx) | Cloud Monitoring | 30-day window |
| Latency p50 / p99 (ms) | Cloud Monitoring | 30-day window |
| Tool calls / day · ok vs failed | Cloud Logging `tool_call` | Real success signal (MCP errors are HTTP 200) |
| Calls by tool | Cloud Logging `tool_call` | Busiest tools |
| Error rate by tool (+ codes) | Cloud Logging `tool_call` | Top failing tools |
| Latency by tool · avg / p99 | Cloud Logging `tool_call` | Per-*tool* latency (Cloud Monitoring is per-HTTP only) |
| Calls by client | Cloud Logging `tool_call` | Load by AI client |
| Client × tool matrix | Cloud Logging `tool_call` | Who calls what |
| AI-client breakdown (doughnut) | Cloud Logging User-Agent | Heuristic; upgrades to `clientInfo` when the MCP middleware emits `mcp_request` events |
| PyPI downloads / day | pypistats.org | No auth needed |
| GitHub stats + views/clones | GitHub API | Views/clones only with `GITHUB_TOKEN` |

### Updating the dashboard

**To change what data is collected** — edit the relevant `collect_*` function in [scripts/dashboard.py](scripts/dashboard.py). Each function returns a plain dict; add keys and they're available in the template automatically.

**To change the layout or charts** — edit [scripts/dashboard_template.html](scripts/dashboard_template.html). The script injects collected data as `const DATA = __DATA__` (JSON) and the generation timestamp as `__GENERATED__`. Chart.js 4.4.1 is loaded from CDN.

**To add a new data source:**
1. Write a `collect_<name>() -> dict` function in `dashboard.py`.
2. Add it to the `payload` dict in `main()`: `"<name>": _collect("<name>", collect_<name>)`.
3. Add the corresponding chart/card JS in `dashboard_template.html` reading from `DATA.<name>`.

**To change the lookback window** — set `LOOKBACK_DAYS` at the top of `dashboard.py` (default: 30).

### Cache

Successful collector results are written to `.dashboard_cache/<name>.json`. The cache is used as a fallback when a source is unavailable. To force a fresh fetch, delete the relevant file:

```bash
rm .dashboard_cache/cloud_run.json   # force Cloud Run re-fetch next run
rm -rf .dashboard_cache/             # clear everything
```

`.dashboard_cache/` and `dashboard.html` are gitignored.
