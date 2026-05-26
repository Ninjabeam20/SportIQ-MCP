---
title: FallbackChain pattern
type: decision
tags: [architecture, resilience]
sources: [chat]
last_updated: 2026-05-26
related: [[fallback-contract]]
---

# ADR 0005 — FallbackChain pattern

## Decision

Every tool routes through a `FallbackChain[T]`. Adapters are pluggable. The chain handles cache lookup, ordered adapter walk, stale-serve, and metadata.

See `.claude/rules/fallback-contract.md` for the contract and `src/sportiq/core/fallback.py` for the implementation.

## Context

Every free data source we use will fail — quotas, scraper IP blocks, upstream outages. A tool that hardcodes one adapter is brittle. A tool that branches manually across sources becomes a tangle.

A uniform chain primitive:
- Centralises the resolution logic (try fresh cache → walk adapters → serve stale → raise).
- Surfaces what happened in `meta` so the AI can phrase responses appropriately ("as of 4 minutes ago…").
- Makes tests trivial: stub the chain output and assert tool behavior.

## Consequences

- Tools cannot bypass the chain. The hard rule in CLAUDE.md is enforced by code review.
- Adapter authors implement a simple `Protocol` (`name`, `async fetch`, `async healthcheck`). Easy to add new sources.
- Per-category chains live in `src/sportiq/{sport}/chains.py` as module-level singletons.

## Status

Accepted.
