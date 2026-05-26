# Operation log

Append-only. Grep with `grep "^## \[" docs/log.md`.

Operations: `ingest` · `decision` · `lint` · `release` · `tool-added` · `adapter-added` · `finding-filed` · `cache-cleared` · `phase-complete`.

## [2026-05-26] phase-complete | Phase 0 — spine
Scaffolded the resilience primitives (`FallbackChain`, cache w/ Redis→diskcache auto-fallback, error envelope, rate limiter, structlog), FastMCP `server.main()` entry point, `sportiq_health` tool, and the full `.claude/` workspace (7 rules, 8 commands, 1 skill, 3 agents, 2 hooks). 6 ADRs filed. Tests cover FallbackChain ordering, cache backend selection, and stale-serve behavior.
