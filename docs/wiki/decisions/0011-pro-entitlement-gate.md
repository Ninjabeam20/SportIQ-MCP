---
title: Pro-entitlement gate (V1 presence check)
type: decision
tags: [monetization, entitlements, gating]
sources: [chat, v1.md]
last_updated: 2026-06-18
related: [[error-envelope]], [[fastmcp-patterns]]
---

# ADR 0011 — Pro-entitlement gate (V1 presence check)

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
server-side on the hosted `/mcp`, where the key is validated against Polar and
clients never see the source.

## The V1 → V2 → V3 boundary

V1 deliberately includes two indirections so **V2 needs no further tool edits**:

- `get_active_key()` — V1 reads the process-wide `settings.sportiq_pro_key`. V2
  swaps the body for a per-request contextvar + Polar validation. Tools call
  `is_pro` / `require_pro`, never the setting, so they don't change.
- `gated(fn)` — wraps each paid tool, preserves name/docstring/signature
  (FastMCP schema unchanged), and tags `__sportiq_gated__` for coverage tests.

V1 = presence check (this ADR). V2 (`v2.md`) = real Polar validation everywhere.
V3 (`v3.md`) = other platforms + hardening.

## Provider-agnostic

The gate checks presence only, so a key from Polar / Lemon Squeezy / Paddle /
Gumroad all work identically. Adding a platform later is zero code change here.

## Consequences

- New error code `SUBSCRIPTION_REQUIRED` (added to the exhaustive
  [[error-envelope]] table).
- `FallbackChain`, adapters, and the free tools are untouched — the gate sits
  above the chain, in the tool wrapper. `instrument_tools` telemetry composes
  over `gated` (telemetry wraps the already-gated `fn`).
- The uvx contract is unchanged: no new deps, no network.
