---
title: FastMCP over raw MCP SDK
type: decision
tags: [mcp, framework]
sources: [chat]
last_updated: 2026-05-26
related: [[fastmcp-patterns]]
---

# ADR 0001 — FastMCP over raw MCP SDK

## Decision

Use `FastMCP` (the decorator-based wrapper inside the `mcp` SDK) instead of constructing `Server` / `Tool` objects directly.

## Context

The MCP SDK ships both APIs. The lower-level one requires manually declaring tool schemas as JSON Schema dicts; FastMCP derives them from Python type hints and docstrings.

## Consequences

- Docstrings + types ARE the schema. Tool authors cannot drift between code and schema.
- Less boilerplate per tool — every tool is ~10 lines.
- Lock-in to the FastMCP API surface (small risk; it's the recommended path).

## Status

Accepted.
