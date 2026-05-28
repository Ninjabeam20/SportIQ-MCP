---
title: f1_undercut_window
type: tool
tags: [f1, undercut, strategy, intel]
sources: []
last_updated: 2026-05-28
related: [[f1-laps-chain]], [[undercut-model]]
---

# f1_undercut_window

Determines if an undercut (pitting early to gain track position) is viable for the attacker vs a target driver.

## Signature

```python
async def f1_undercut_window(session_key: int, attacker_number: int, target_number: int, current_lap: int) -> dict
```

## Args
- `session_key` — OpenF1 session key (obtain from `f1_get_sessions`).
- `attacker_number` — Driver number of the car attempting the undercut.
- `target_number` — Driver number of the car being undercut.
- `current_lap` — Current race lap number.

## Success response

```json
{
  "data": {
    "viable": true,
    "laps_to_clear": 4,
    "net_gain_per_lap": 0.6,
    "verdict": "VIABLE"
  },
  "meta": {"source": "openf1", "is_stale": false}
}
```

`verdict` is one of `VIABLE`, `MARGINAL`, or `NOT_VIABLE`.

## Chain

[[f1-laps-chain]]
