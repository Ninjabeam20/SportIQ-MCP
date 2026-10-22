---
title: "ADR-0013: MCP SDK v2 migration"
type: decision
tags: [mcp, sdk, fastmcp, opentelemetry, dependencies]
sources: [2026-10-22-full-audit, docs/audits/2026-10-22-full-audit.md]
last_updated: 2026-10-22
related: [[0001-fastmcp-over-raw-mcp]], [[0012-hosted-abuse-controls]], [[stateless-lifespan-teardown]], [[2026-10-22-full-audit]]
---

# ADR-0013: MCP SDK v2 migration

SportIQ stays on the MCP Python SDK 1.x (`mcp>=1.30.0,<2`) for the 0.4 release. Moving to SDK v2 is
proposed for a later release because v2 breaks several internals SportIQ relies on and adds OpenTelemetry,
which the frozen stack excludes.

## Status

**Proposed** — 2026-10-22. Owner decision D9 (opus remediation): stay on 1.x (`>=1.30.0,<2`) this
release; revisit after 2026-12-06 and before March 2027. The 1.x line now receives security fixes only.

## Context

The [[2026-10-22-full-audit]] recorded these breaking points for SDK v2:

- `mcp.server.fastmcp` is removed; the class is now `MCPServer`.
- `mcp._mcp_server` becomes `_lowlevel_server`. `server.py` binds the server version through it.
- The `_tool_manager._tools` reach-ins in `core/tool_telemetry.instrument_tools` and
  `core/param_docs.apply_param_descriptions` stop resolving. Both no-op silently today when the
  registry moves; `test_instrument_tools_wrapped_every_registered_tool` and
  `test_param_descriptions_applied_to_live_schema` now fail loudly instead.
- The `stateless_http` setting moves to `streamable_http_app()`.
- The lifespan runs once per process, so the shutdown-only singleton close in `server.build_http_app`
  ([[stateless-lifespan-teardown]]) becomes unnecessary (harmless to keep).
- **`opentelemetry-api` becomes a hard dependency with tracing on by default.** That conflicts with the
  frozen "no OpenTelemetry" stack decision in `CLAUDE.md`.

## Options

- **(a) Migrate** and accept OpenTelemetry as a transitive dependency, with tracing disabled through the
  SDK's environment switch. Requires a stack amendment.
- **(b) Stay on 1.x** until its end of life, taking 1.x security releases (`>=1.30.0,<2`).

## Decision

(b) for this release (D9). Re-decide between (a) and (b) in the window above, in a dedicated branch
that is not combined with any hosting change.

## Consequences

- `pyproject.toml` keeps the `<2` ceiling; Dependabot/uv upgrades must not lift it.
- The two guard tests above are the early warning if a 1.x release moves the same internals.
