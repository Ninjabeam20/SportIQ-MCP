---
title: "ADR-0009: Redact secrets at the fallback capture point"
type: decision
tags: [security, fallback, error-envelope, secrets]
sources: []
last_updated: 2026-06-03
related: [[error-envelope-secret-leak]], [[cricapi-envelope-leak]], [[0005-fallback-chain-pattern]], [[cricapi]]
---

# ADR-0009: Redact secrets at the fallback capture point

## Status

Accepted — 2026-06-03 (step10 Phase S.1)

## Context

API keys for CricAPI and The Odds API travel as URL **query params** (those APIs
have no header-auth option). `core/http.py:get_json()` raises
`httpx.HTTPStatusError` whose string embeds the full request URL, and
`core/fallback.py` captured that string into `attempts[].error` → the error
envelope's `sources_tried`, plus the failure log. Result: a 4xx/5xx from a keyed
source disclosed the key to the MCP client/LLM. CI hid it (no keys present). See
[[error-envelope-secret-leak]]. This is distinct from the success-body echo fixed
earlier (see [[cricapi-envelope-leak]]).

## Decision

Introduce a single redaction choke point, `core/redact.py:scrub(text)`, and apply
it where exceptions become stored/emitted strings — at the two
`core/fallback.py` capture sites (the attempt `error` field and the failure-log
field). `scrub` redacts three ways:

1. **Structural query params** — names matched positionally after `?`/`&`
   (`apikey`, `api_key`, `token`, `secret`, `signature`, `key`, …), so a
   non-secret param that merely contains "key" (OpenF1's `session_key`) is left
   intact.
2. **Auth headers** — `Authorization`/bearer, `x-rapidapi-key`, `x-api-key`.
3. **Literal credential values** read from `settings` — a value-based backstop
   that catches a key regardless of where it sits in the string.

## Alternatives considered

- **Scrub inside `get_json` (re-raise a sanitized error).** Rejected: re-raising
  inside the tenacity-retried function would change the exception type and defeat
  `core/http.py:_should_retry`, breaking the 5xx/transport retry policy. The leak
  is fully closed at the capture point instead.
- **Move keys to headers.** Not possible for CricAPI / The Odds API (query-only
  auth). RapidAPI / football-data.org / API-Football already use headers and are
  still scrubbed defensively.

## Consequences

- The error envelope's `sources_tried` and the chain failure log are secret-safe;
  regression-locked by `tests/unit/test_redact.py` (8) and
  `tests/chains/test_chain_key_redaction.py` (2).
- `scrub` is the canonical sanitizer — any future site that turns an exception or
  URL into a stored/logged string should route through it.
- **Out of scope (tracked in step10 Phase S):** S.5 wraps `structlog` with a
  redaction processor so *all* log events are scrubbed, not just the chain
  failure log; S.6 restricts `core/http.py` redirects to same-host so a key in a
  URL cannot be bounced to another host.
