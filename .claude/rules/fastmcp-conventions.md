# FastMCP conventions

Docstrings + type hints **are** the MCP schema. Treat them as production interface, not documentation.

## Rules

- Every `@mcp.tool()` function MUST have:
  - Fully-typed parameters (no `Any`, no untyped `dict`).
  - A docstring whose first line is a one-sentence action description (used by the model to choose the tool).
  - A docstring `Args:` block describing every parameter (used by the model to fill them).
  - A return type annotation. Pydantic models preferred for structured returns.
- The return type for SportIQ tools is always `core.tool_response.Envelope`, the sanctioned
  exception to "Pydantic preferred." Its open payload fields preserve one uniform success/error
  envelope without FastMCP null-filling every possible per-tool field.
- Tool names are `{sport}_{verb}_{noun}` snake_case. Examples: `cricket_get_live_matches`, `f1_predict_pit_strategy`, `football_simulate_bracket`.
- Tools live in `src/sportiq/{sport}/tools.py` and are registered by importing that module in `server.py`.
- Tool bodies stay thin: validate args → call a `FallbackChain` → wrap result in `{data, meta}` envelope. No business logic.
- Business logic lives in `src/sportiq/{sport}/models/`. Pure functions, no I/O.

## Anti-patterns

- ❌ `async def cricket_get(args: dict)` — untyped dict erases the schema.
- ❌ Calling `httpx.AsyncClient` from `tools.py` — bypasses the chain.
- ❌ Returning raw upstream JSON — caller has no idea which source it came from.
- ❌ Catching exceptions in tools and returning `{"ok": False}` ad hoc — use the error envelope.
