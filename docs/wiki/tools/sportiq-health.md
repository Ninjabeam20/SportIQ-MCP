---
title: sportiq_health
type: tool
tags: [meta, health, quota, cache]
sources: [src/sportiq/core/health.py]
last_updated: 2026-10-22
related: [[0003-redis-with-diskcache-fallback]], [[0005-fallback-chain-pattern]], [[stateless-lifespan-teardown]]
---

# sportiq_health

Reports the cache backend, every registered adapter's healthcheck, and the remaining quota per budgeted source, so a caller can ask "is anything down?" in one call.

## Signature
```python
async def sportiq_health() -> Envelope
```
No arguments. Registered read-only (`READ_ONLY` annotations).

## Returns
`data` is a `HealthReport`:
- `cache_backend` — `redis` or `diskcache`. **`diskcache` is a healthy state**, the local-dev default and
  the automatic fallback when Redis is unset or unreachable ([[0003-redis-with-diskcache-fallback]]).
- `cache_ok` — the backend's own healthcheck.
- `adapters` — `[{name, ok, detail}]`, one row per upstream. Chains register adapters through
  `register_adapter_for_health()`, deduplicated by `health_name` (the first registration wins), so the
  several CricAPI adapter classes report once. A missing key shows as `ok: false`, never an exception.
- `quotas` — remaining tokens per `Budget.source` (per day, plus `<source>:per_minute` where a minute cap
  exists).

`meta.version` is the package version.

## Not a chain tool
This meta-tool reads registry state and does not go through a `FallbackChain`; it never calls a
quota-capped API (each adapter's `healthcheck()` only checks credentials/config).

## Versus `GET /healthz`
`/healthz` is an HTTP-only liveness route that returns `200 ok` without touching the cache, chains or
network. The Docker HEALTHCHECK probes it. `sportiq_health` is the MCP tool for a fuller report. See
[[stateless-lifespan-teardown]] for why the HEALTHCHECK moved off `/mcp`.
