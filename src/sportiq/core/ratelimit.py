"""Per-source token bucket. Counters stored in the unified cache."""

from __future__ import annotations

import time
from dataclasses import dataclass

from sportiq.core.cache import get_cache


@dataclass(frozen=True)
class Budget:
    source: str
    per_minute: int | None = None
    per_day: int | None = None


async def check_and_consume(budget: Budget) -> bool:
    """Return True if the request is within budget AND consume one token.

    Returns False if budget is exhausted — the chain skips this adapter.
    """
    cache = get_cache()
    now = int(time.time())

    if budget.per_minute is not None:
        minute_bucket = now // 60
        key = f"ratelimit:{budget.source}:minute:{minute_bucket}"
        entry = await cache.get(key)
        used = entry.value if entry else 0
        if used >= budget.per_minute:
            return False
        await cache.set(key, used + 1, ttl_seconds=120)

    if budget.per_day is not None:
        day_bucket = now // 86400
        key = f"ratelimit:{budget.source}:day:{day_bucket}"
        entry = await cache.get(key)
        used = entry.value if entry else 0
        if used >= budget.per_day:
            return False
        await cache.set(key, used + 1, ttl_seconds=172800)

    return True


async def remaining(budget: Budget) -> dict[str, int | None]:
    cache = get_cache()
    now = int(time.time())
    out: dict[str, int | None] = {}

    if budget.per_minute is not None:
        minute_bucket = now // 60
        entry = await cache.get(f"ratelimit:{budget.source}:minute:{minute_bucket}")
        used = entry.value if entry else 0
        out["per_minute"] = max(0, budget.per_minute - used)
    if budget.per_day is not None:
        day_bucket = now // 86400
        entry = await cache.get(f"ratelimit:{budget.source}:day:{day_bucket}")
        used = entry.value if entry else 0
        out["per_day"] = max(0, budget.per_day - used)
    return out
