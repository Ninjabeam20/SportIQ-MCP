---
title: API key leak via the error envelope
type: finding
tags: [security, fallback, cricapi, theodds, error-envelope]
sources: [chat, 2026-06-03-step10-s1, core/http.py, core/fallback.py]
last_updated: 2026-06-03
related: [[cricapi-envelope-leak]], [[0009-secret-redaction]], [[0005-fallback-chain-pattern]], [[cricapi]], [[cricket-get-live-odds]], [[football-get-odds]]
---

# API key leak via the error envelope

On any upstream failure, the API key for a query-param-auth source (CricAPI, The
Odds API) leaked to the MCP client/LLM through the **error** envelope's
`sources_tried` — because the captured exception string contained the request URL,
and the key rides in that URL.

This is a **different vector** from [[cricapi-envelope-leak]]: that one leaked the
key in the *success* `{data}` body (raw upstream echo, fixed via `_unwrap`). This
one leaks it on the *failure* path, and spans CricAPI **and** both The Odds API
adapters.

## What happened

`core/http.py:get_json()` calls `response.raise_for_status()`, raising
`httpx.HTTPStatusError` whose `str()` embeds the full request URL, e.g.
`Client error '401 Unauthorized' for url 'https://api.cricapi.com/v1/currentMatches?apikey=SECRET&offset=0'`.

CricAPI (`apikey=`) and The Odds API — both `cricket/adapters/theodds.py` and
`football/adapters/theodds.py` (`apiKey=`) — pass the key as a **query param**
(no header-auth option). `core/fallback.py` captured the exception string into the
attempt log:

```python
attempts.append({..., "error": f"{type(e).__name__}: {e}"})   # <- URL w/ key
log.warning("chain.adapter.failed", ..., error=str(e))         # <- URL w/ key
```

`attempts` is handed to the tool, which surfaces it as the error envelope's
`sources_tried` (see [[0005-fallback-chain-pattern]]). So a 4xx/5xx from a keyed
source disclosed the key to the caller and to logs.

Why it hid: CI has no keys, so the URL carried no secret and every test passed.
The leak only fires when a real key is present (operator/local `.env`).

## Fix

New `core/redact.py:scrub(text)` — a single choke point that redacts:

1. **Known-secret query params** — matched *positionally* right after `?`/`&`
   (`apikey`, `api_key`, `token`, `secret`, …) so non-secret params that merely
   contain "key" (OpenF1's `session_key`) are left intact.
2. **Auth headers** — `Authorization: Bearer …`, `x-rapidapi-key`.
3. **Literal credential values** from `settings` — a value-based backstop that
   catches a key wherever it appears.

Applied at both `fallback.py` capture sites (attempt `error` + failure log). It
is **not** applied inside `get_json`: re-raising there would change the exception
type and defeat `core/http.py:_should_retry` (tenacity). The envelope leak is
fully closed at the capture point; broader log-processor redaction is tracked as
step10 S.5, same-host-redirect hardening as S.6. Rationale recorded in
[[0009-secret-redaction]].

CricAPI + The Odds API have no header-auth alternative, so `scrub` is their only
mitigation — keep it airtight.

## Regression coverage

- `tests/unit/test_redact.py` (8): query-param (lower + camel), Authorization
  bearer, x-rapidapi-key, value-based redaction, `session_key` preserved,
  clean-text unchanged, empty inputs.
- `tests/chains/test_chain_key_redaction.py` (2): a real `httpx.HTTPStatusError`
  with a key-bearing URL driven through a `FallbackChain` → the key appears
  **nowhere** in `attempts` or the error envelope's `sources_tried`.

> Test filename note: it is `test_chain_key_redaction.py`, not `…_redacts_secrets`,
> because the old `.gitignore` `*secret*` rule silently ignored any path containing
> "secret" (since narrowed to extension/name-scoped secret patterns).

## Status

Shipped 2026-06-03 (commit `4ddd8f6`). Suite 318 → 328, coverage 87%.
Follow-ups: S.5 (log-processor redaction), S.6 (same-host redirects) — step10 Phase S.
