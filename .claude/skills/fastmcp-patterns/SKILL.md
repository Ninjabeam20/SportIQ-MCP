---
name: fastmcp-patterns
description: Patterns for FastMCP tool authoring — registration, typed I/O, envelope responses, error handling, async chains. Invoke when scaffolding or modifying any @mcp.tool() function.
---

# FastMCP patterns

The decorator API maps Python signatures directly to JSON Schema. Docstrings + types = the contract.

## Minimal tool

```python
from sportiq.server import mcp
from sportiq.cricket.chains import live_matches_chain
from sportiq.core.tool_response import tool_response, error_envelope
from sportiq.core.errors import AllSourcesFailedError

@mcp.tool()
async def cricket_get_live_matches() -> dict:
    """Return currently live cricket matches.

    Returns:
        Envelope with `data.matches` (list) and `meta` (source, is_stale, ...).
    """
    try:
        result = await live_matches_chain.fetch()
    except AllSourcesFailedError as e:
        return error_envelope(
            code="ALL_SOURCES_FAILED",
            message="No cricket data source reachable.",
            sources_tried=e.attempts,
        )
    return tool_response(result)
```

## Tool with input

```python
from pydantic import Field

@mcp.tool()
async def cricket_get_scorecard(
    match_id: str = Field(..., description="CricAPI match_id, e.g. 'a1b2c3'."),
) -> dict:
    """Return the full scorecard for a single match."""
    result = await scorecard_chain.fetch(match_id=match_id)
    return tool_response(result)
```

## Returning a pydantic model

If the return shape is stable, use a pydantic model — the MCP schema becomes typed JSON Schema instead of a free dict.

```python
class HealthReport(BaseModel):
    cache_backend: Literal["redis", "diskcache"]
    adapters: dict[str, bool]
    quotas: dict[str, int]

@mcp.tool()
async def sportiq_health() -> HealthReport:
    """Report cache backend, per-adapter healthcheck, remaining quotas."""
    ...
```

## Gotchas

- `Field(..., description=...)` is required — the description flows into the MCP schema.
- Do NOT use `Optional[X]`; use `X | None` (Python 3.10+ syntax) — FastMCP handles both, but the typing is cleaner.
- For long-running tools, accept a `ctx` parameter and call `await ctx.report_progress(...)`.
- Tools registered in `tools.py` are only registered if `server.py` imports that module. Don't forget.
