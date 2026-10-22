---
title: Stateless HTTP Ran the FastMCP Lifespan Per Request
type: finding
tags: [http, mcp-sdk, lifespan, cache, production-bug]
sources: [docs/audits/2026-10-22-full-audit.md, src/sportiq/server.py]
last_updated: 2026-10-22
related: [[2026-10-22-full-audit]], [[diskcache-expire-purge]], [[sportiq-health]], [[home-server-cutover]], [[0012-hosted-abuse-controls]]
---

# Stateless HTTP Ran the FastMCP Lifespan Per Request

In stateless streamable-HTTP mode the MCP SDK enters the FastMCP lifespan once per request, so SportIQ's lifespan cleanup closed the shared cache and HTTP client after every request — the root cause of all 11 production `AttributeError`s.

## Mechanism
- `server.py` passes `lifespan=_lifespan` to `FastMCP(...)`; its `finally` ran `close_client()` and
  `close_cache()`.
- With `mcp.settings.stateless_http = True`, the SDK's `run_stateless_server`
  (`mcp/server/streamable_http_manager.py`) starts a fresh low-level server run per request, and each run
  enters the lifespan (`mcp/server/lowlevel/server.py`).
- So request B's teardown nulled the singletons while request A was still in flight. A's next
  `get_cache().set(...)` hit `None` → `'NoneType' object has no attribute 'set'`. Three overlapping calls
  failed together in the 2026-10-05 logs.
- Side effects: no HTTP connection reuse, and a retry on a fresh client could hit an upstream twice for
  one budget token.
- The Docker HEALTHCHECK `GET /mcp` every 30 s (60% of logged `mcp_request` events) widened the window.

## Fix (2026-10-22)
- `_lifespan` cleans up only under stdio, where it runs once per process.
- `build_http_app()` wraps the Starlette app's `lifespan_context`, so `_close_shared_resources()` runs
  **once at app shutdown**, after the SDK's session manager exits.
- A non-MCP `GET /healthz` returns `200 ok` without touching the cache, chains or network; the Docker
  HEALTHCHECK probes it instead of `/mcp`.
- Regression test: `tests/unit/test_server_stateless_concurrency.py` overlaps a slow tool call with two
  `tools/list` requests through the real ASGI app and asserts no `Error executing tool`.

## Lesson
A lifespan hook is per **run**, and stateless mode makes every request a run. Process-wide resources
belong to the ASGI app's lifespan. The `cross_sport_build_accumulator` re-raise was not the bug and stays
as is: it only surfaced this root cause.
