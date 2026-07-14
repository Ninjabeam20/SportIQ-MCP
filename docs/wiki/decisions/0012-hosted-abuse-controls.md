---
title: "ADR-0012: Hosted abuse controls"
type: decision
tags: [security, http, rate-limit, telemetry, cache]
sources: [design, implementation]
last_updated: 2026-07-14
related: [[0003-redis-with-diskcache-fallback]], [[local-analytics-dashboard]], [[fastmcp-patterns]]
---

# ADR-0012: Hosted abuse controls

## Status

Accepted on `codex_changes` — 2026-07-14. The branch did not deploy or mutate Cloud Run.

## Context

The public streamable-HTTP endpoint previously had no application request-body or request-rate
boundary. Client telemetry could retain an entire initialize body, and CPU-heavy simulations,
strategy models, and the Dream11 solver could all enter concurrently. Provider quota counters
also used a non-atomic read-modify-write sequence.

## Decision

- `core/request_limits.py` is pure ASGI so MCP streaming responses remain unbuffered. It admits
  only POST `/mcp` traffic through the controls, caps bodies at 1 MiB, and returns HTTP 413 before
  FastMCP dispatch.
- Each process permits 60 requests per hashed client identity and 300 total requests per minute.
  Excess traffic receives HTTP 429 plus `Retry-After: 60` before MCP envelope handling.
- The validated rightmost `X-Forwarded-For` IP appended by Cloud Run is trusted only when its
  `K_SERVICE` marker exists. Other environments use the ASGI peer IP; raw identities never enter
  counter keys.
- `core/cache.py` provides atomic raw counters: diskcache transaction locally and Redis
  INCR/first-expiry Lua when configured.
- `core/client_info.py` captures at most 64 KiB for initialize inspection while forwarding every
  accepted byte, and sanitizes/caps logged client fields and User-Agent.
- `core/tool_telemetry.py` owns one semaphore of size two for exactly the three football
  simulation tools, F1 pit strategy, and Dream11 team builder. Queue time remains part of logged
  latency.

## Deployment invariant

The request counters are per process. Cloud Run must therefore use `--max-instances=1`; raising
the instance ceiling multiplies the effective global limit and requires shared admission control
first. Stdio is unaffected. HTTP 413/429 responses occur before MCP envelopes.

## Consequences

The public boundary now has deterministic memory, request-rate, telemetry-capture, and expensive
work limits without introducing a new service or requiring Redis for local development. A single
instance limits horizontal availability and throughput; that is an explicit security/cost tradeoff
until admission state is externalized.

The existing upstream 10 MiB response ceiling is still enforced after httpx buffers a response;
it is not streaming ingress protection. Provider budget admission also retains the
peek→fetch→consume race even though counter increments themselves are now atomic. Neither caveat
was hidden, and no live deployment validation occurred on this branch.
