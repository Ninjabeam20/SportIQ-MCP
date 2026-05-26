# Fallback contract

Every tool MUST route through a `FallbackChain`. Never call an adapter directly.

## The contract

`src/sportiq/core/fallback.py` defines:

```python
class Adapter(Protocol, Generic[T]):
    name: str
    async def fetch(self, **kwargs) -> T: ...
    async def healthcheck(self) -> bool: ...

class FallbackResult(Generic[T]):
    value: T
    source: str            # which adapter served it (or "cache:stale")
    is_stale: bool
    attempts: list[dict]   # [{name, status, error?, duration_ms}, ...]

class FallbackChain(Generic[T]):
    name: str
    adapters: list[Adapter[T]]
    cache_key_fn: Callable[..., str]
    fresh_ttl: int
    stale_ttl: int

    async def fetch(self, **kwargs) -> FallbackResult[T]: ...
```

## Resolution order

1. Try fresh cache. Hit → return.
2. Walk adapters in declared order. First success → cache write + return.
3. All adapters fail. Try stale cache (within `stale_ttl`). Hit → return with `is_stale=True`.
4. No stale cache available → raise `AllSourcesFailedError`. The tool wraps this into the error envelope.

## Tool integration

```python
@mcp.tool()
async def cricket_get_live_matches() -> dict:
    """Return currently live cricket matches."""
    try:
        result = await live_matches_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(code="ALL_SOURCES_FAILED", attempts=e.attempts)
    return tool_response(result)  # builds {data, meta} envelope
```

## Anti-patterns

- ❌ Bypassing the chain ("just this once, the adapter is faster").
- ❌ Swallowing `is_stale=True` instead of surfacing it in `meta`.
- ❌ Defining chains inside tool bodies. Chains are module-level singletons in `chains.py`.
