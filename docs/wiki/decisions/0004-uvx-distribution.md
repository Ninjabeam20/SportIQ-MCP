---
title: uvx distribution
type: decision
tags: [packaging, distribution]
sources: [chat]
last_updated: 2026-05-26
related: []
---

# ADR 0004 — uvx as the primary distribution channel

## Decision

Ship via `uvx`. `pyproject.toml` declares:

```toml
[project.scripts]
sportiq-mcp = "sportiq.server:main"
```

`src/sportiq/server.py` exposes `main()` which calls `mcp.run()`. End users install with:

```bash
uvx sportiq-mcp
```

## Context

The MCP audience overlaps heavily with `uv` users (fast install, isolated envs, no global pollution). `pipx` would also work but adds a second install path. Picking one keeps the README short.

## Consequences

- Anyone with `uv` can run the server in one command.
- The `[project.scripts]` entry MUST stay stable across releases — it's the public contract.
- Claude Desktop config snippet in README must use the `uvx` form.

## Status

Accepted.
