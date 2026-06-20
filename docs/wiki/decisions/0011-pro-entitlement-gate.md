---
title: Pro-entitlement gate (V1 presence check + V2a hosted enforcement)
type: decision
tags: [monetization, entitlements, gating]
sources: [chat, v1.md, v2.md]
last_updated: 2026-06-20
related: [[error-envelope]], [[fastmcp-patterns]]
---

# ADR 0011 — Pro-entitlement gate (V1 presence check + V2a hosted enforcement)

## Decision

Gate the 24 intelligence tools behind a non-blank `SPORTIQ_PRO_KEY`. The ~19 raw
data tools and `sportiq_health` stay free. V1 is an **honor-system presence
check**: any non-blank key unlocks; the key is not validated against anything.

The gate lives in `core/entitlements.py` (`PAID_TOOLS`, `get_active_key`,
`is_pro`, `require_pro`, `gated`) and is applied at tool **registration**:
`mcp.tool(...)(gated(fn))`. Locked calls return a `SUBSCRIPTION_REQUIRED`
envelope with the checkout link; the tool body never runs.

## Why honor-system is acceptable (V1)

A locally-installed package can always be patched to remove the gate — true of
all locally-distributed software. V1 accepts this. The value is the friction +
the checkout funnel, not cryptographic enforcement. Real enforcement is V2,
server-side on the hosted `/mcp`, where the key is validated against a key source
the operator controls and clients never see the source.

## The V1 → V2 → V3 boundary

V1 deliberately includes two indirections so **V2 needs no further tool edits**:

- `get_active_key()` — resolves a per-request contextvar (hosted, set by
  `ProKeyMiddleware`) then the process-wide `settings.sportiq_pro_key` (local).
  Tools call `is_pro` / `require_pro`, never the setting, so they don't change.
- `gated(fn)` — wraps each paid tool, preserves name/docstring/signature
  (FastMCP schema unchanged), and tags `__sportiq_gated__` for coverage tests.

V1 = presence check. V2 (`v2.md`) = hosted online enforcement. V3 (`v3.md`) =
other platforms + hardening.

## V2a — hosted shared-key enforcement (implemented 2026-06-20)

On the hosted `/mcp`, validate the per-request key against a configured set
rather than just checking presence:

- `core/license.py` — `LicenseValidator` Protocol + `SharedKeyValidator`, which
  checks membership in `SPORTIQ_VALID_KEYS` (a comma-separated Cloud Run secret).
  `validate_key()` is the single entry point; when the set is **unset** (local
  stdio) it falls back to the V1 presence check (any non-blank key). V2b swaps in
  a `KeystoreValidator` (per-user keys from the sponsorship webhook) behind the
  same Protocol — no gate change.
- `core/pro_middleware.py` — `ProKeyMiddleware`, pure ASGI (NOT
  `BaseHTTPMiddleware`, which breaks MCP streamable-HTTP SSE). Extracts the key
  from a `/u/<key>/mcp` URL path (rewriting it to `/mcp`) or an
  `Authorization: Bearer` header, binds it to the request contextvar, resets
  after. Attached after `ClientInfoMiddleware` (outermost) on HTTP only.
- `require_pro()` now raises `SUBSCRIPTION_REQUIRED` for a *missing* key (one
  message) or an *unrecognised* key (a distinct message).

Local installs keep working unchanged (no `SPORTIQ_VALID_KEYS` → presence mode).

## Provider-agnostic

The validator is presence-or-membership, so a key from any provider works
identically. Adding a platform later is a validator swap, not a tool change.

## Consequences

- New error code `SUBSCRIPTION_REQUIRED` (added to the exhaustive
  [[error-envelope]] table).
- `FallbackChain`, adapters, and the free tools are untouched — the gate sits
  above the chain, in the tool wrapper. `instrument_tools` telemetry composes
  over `gated` (telemetry wraps the already-gated `fn`).
- The uvx contract is unchanged: no new deps, no network.
