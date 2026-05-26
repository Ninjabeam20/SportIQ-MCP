---
title: Redis with diskcache fallback
type: decision
tags: [cache, infra]
sources: [chat]
last_updated: 2026-05-26
related: [[caching-policy]]
---

# ADR 0003 — Redis with diskcache fallback

## Decision

`core/cache.py` exposes one interface. The backend is Redis if `REDIS_URL` is set and the daemon is reachable; otherwise it silently uses `diskcache` rooted at `~/.cache/sportiq/`.

**Local dev assumes diskcache.** Do not write code, tests, or health checks that require a running Redis daemon. The `diskcache` backend is a healthy state for local dev — not degraded.

## Context

`uvx sportiq-mcp` users won't have Redis. Forcing a Redis daemon would kill the "install in 30 seconds" pitch. But hosted/production deployments want Redis for cross-process sharing and TTL precision.

## Consequences

- One interface, two backends. Tests stub the cache singleton with an isolated diskcache directory (see `tests/conftest.py`).
- `sportiq_health()` reports the active backend.
- Rate-limit counters live in the same store, so they degrade together — acceptable since per-process limits are conservative.

## Status

Accepted.
