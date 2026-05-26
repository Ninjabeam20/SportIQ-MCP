---
title: respx for HTTP test mocking
type: decision
tags: [testing, http]
sources: [chat]
last_updated: 2026-05-26
related: [[testing]]
---

# ADR 0006 — respx for HTTP test mocking

## Decision

Mock `httpx` calls in tests with `respx`. Cassettes are JSON files committed to `tests/fixtures/{source}/`.

## Context

We need adapter tests that exercise our parsers against real upstream response shapes — but never hit the network in CI.

`respx` ships native `httpx` integration, supports route assertions (was the call made? with what params?), and accepts plain JSON fixtures.

Alternatives considered:
- `pytest-vcr` — cassette format is YAML; less ergonomic.
- Hand-rolled monkeypatching of `httpx.AsyncClient.get` — fragile, no assertion helpers.

## Consequences

- Adapter tests can be confident about request shape AND response handling.
- New adapters need a recorded fixture before they can be committed — forces the author to document the response shape.
- CI runs deterministically. No flake from upstream latency.

## Status

Accepted.
