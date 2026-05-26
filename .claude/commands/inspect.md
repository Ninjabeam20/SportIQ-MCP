---
description: Launch the MCP inspector against the local sportiq server.
---

# /project:inspect

Launch `@modelcontextprotocol/inspector` so you can poke at the tool schemas in a browser.

## Command

```bash
npx @modelcontextprotocol/inspector uv run python -m sportiq.server
```

## What to verify

- Every tool appears with the correct schema (no `Any` types).
- Every parameter has a description.
- Return types are structured (no untyped dicts where a pydantic model would do).
- `sportiq_health` returns the live status matrix.

## When to run

- After adding any tool (per `/project:add-tool`).
- Before any release.
- When the user says "did my tool register?"
