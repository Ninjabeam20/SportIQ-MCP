---
description: Clear a Redis/diskcache namespace by sport or tool.
argument-hint: <sport>[:tool_name]
---

# /project:refresh-cache $ARGUMENTS

Clear cache entries for a sport or a specific tool.

Examples:
- `/project:refresh-cache cricket` → clears `sportiq:cricket:*`
- `/project:refresh-cache cricket:live_score` → clears `sportiq:cricket:live_score:*`

## Workflow

1. **Confirm with user** before clearing. Cache wipes can amplify upstream rate-limit pressure.
2. Detect active backend via `sportiq_health()`. Use the appropriate clear:
   - Redis: `SCAN` + `DEL` by pattern.
   - diskcache: `cache.evict(tag=...)`.
3. Report number of keys cleared.
4. **Append to `docs/log.md`:** `## [YYYY-MM-DD] cache-cleared | {pattern}`.

## Hard rules

- NEVER run `FLUSHALL` or `cache.clear()` — always scoped by pattern.
- NEVER clear `ratelimit:*` — that resets quota tracking and lies to the chain about budget.
