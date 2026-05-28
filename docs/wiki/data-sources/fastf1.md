---
title: FastF1
type: data-source
tags: [f1, laps, standings, offline, optional]
sources: []
last_updated: 2026-05-28
related: [[f1-laps-chain]], [[f1-standings-chain]]
---

# FastF1

Optional Python library for offline F1 lap and telemetry data. Lazy-imported; not required for production. Serves as a fallback when OpenF1/Jolpica are unavailable.

## Install

```bash
pip install 'sportiq-mcp[f1]'
# or
uv pip install 'sportiq-mcp[f1]'
```

## Credentials

None. Data is fetched from the F1 timing stream cache maintained by the fastf1 project.

## Free-tier limits

None. Data is sourced from official F1 timing archives.

## Adapter behavior

- Module is lazy-imported at first use. If not installed, `healthcheck()` returns `False` and the chain skips this adapter.
- Used as fallback in [[f1-laps-chain]] and [[f1-standings-chain]].
- Local cache stored in `~/.cache/fastf1/` (managed by the fastf1 library).
