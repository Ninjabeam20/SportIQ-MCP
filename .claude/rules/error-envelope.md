# Error envelope

Every tool returns either a `{data, meta}` success envelope or an `{error}` failure envelope. Never both, never neither.

## Success envelope

```json
{
  "data": { ... tool-specific payload ... },
  "meta": {
    "source": "cricapi",
    "is_stale": false,
    "data_age_seconds": 12,
    "fallback_used": false,
    "duration_ms": 187
  }
}
```

The AI sees `is_stale: true` and adapts wording ("As of about 4 minutes ago…").

## Error envelope

```json
{
  "error": {
    "code": "ALL_SOURCES_FAILED",
    "message": "Human-readable explanation",
    "sources_tried": [
      {"name": "cricapi", "error": "429 rate limit"},
      {"name": "cricbuzz_scraper", "error": "timeout after 5s"}
    ],
    "retry_after_seconds": 60,
    "suggestion": "Try cricket_get_live_matches without live filter."
  }
}
```

## Error codes (exhaustive)

| Code | When |
| :--- | :--- |
| `ALL_SOURCES_FAILED` | Every adapter in the chain raised; no stale cache. |
| `RATE_LIMITED` | A specific source returned 429 AND no fallback succeeded. |
| `INVALID_INPUT` | pydantic validation failed before any I/O. |
| `UPSTREAM_TIMEOUT` | All upstreams exceeded timeout; subset of `ALL_SOURCES_FAILED`. |
| `NOT_FOUND` | Source responded successfully but the requested entity does not exist. |
| `SUBSCRIPTION_REQUIRED` | A paid (intel) tool was called without an active `SPORTIQ_PRO_KEY`. |

`code` is mandatory. `message` is mandatory. The other fields are populated when applicable.

## Implementation

`core/errors.py` defines `SportiqError` and subclasses; `core/tool_response.py` exposes `error_envelope(...)` and `tool_response(...)` helpers. Tools call those — never construct envelopes by hand.
