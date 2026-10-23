---
title: "ADR-0014: Hosted image excludes fastf1"
type: decision
tags: [docker, f1, fastf1, pandas, dependencies, hosting]
sources: [2026-10-22-full-audit, docs/audits/2026-10-22-full-audit.md]
last_updated: 2026-10-22
related: [[0004-uvx-distribution]], [[0013-mcp-sdk-v2-migration]], [[product-hosting-arc]], [[2026-10-22-full-audit]]
---

# ADR-0014: Hosted image excludes fastf1

The hosted Docker image no longer installs the `f1` extra (fastf1 with matplotlib, pillow and fontTools),
and `pandas` moves from the base dependencies into that extra. This touches the frozen stack, so it is
recorded here.

## Status

**Accepted** — 2026-10-22, owner decision D8 (opus remediation, cook12 T12.4).

## Context

- The FastF1 laps fallback only knows two hard-coded session keys and has no 2026 sessions.
- The FastF1 standings fallback downloads about 24 sessions in a thread that cannot be cancelled.
- `--extra f1` added about 55 MB (matplotlib, pillow, fontTools), and pillow carried most of the image's
  audit advisories.
- `pandas` (about 48 MB) was a base dependency, but no SportIQ module imports it; only fastf1 uses it.

## Decision

- `Dockerfile` exports `uv export --frozen --no-dev --no-emit-project` (no `--extra f1`).
- `pyproject.toml`: `f1 = ["fastf1>=3.4.0", "pandas>=2.2.0"]`; `pandas` is removed from the base list.
- `sportiq_health` reports an adapter whose `optional_import` module is absent as
  `ok: true, detail: "not installed"`. That is an expected state, not an outage.
- When fastf1 is absent the FastF1 adapters raise `RuntimeError`, which the chain treats as a normal
  failure and walks past (OpenF1 and Jolpica serve first).

## Consequences

- Self-hosters who want the FastF1 fallbacks install `sportiq-mcp[f1]`; nothing else changes for uvx users.
- The image size before and after is recorded in the opus cook13 Phase B notes.
- `CLAUDE.md`/`AGENTS.md` and `PROJECT.md` stack rows now say pandas lives in the `f1` extra.
