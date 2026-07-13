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


async def has_budget(budget: Budget) -> bool:
    """Peek: return True if a request is within budget. Does NOT consume.

    The chain calls this before an adapter's fetch() and only :func:`consume`s a
    token after the fetch succeeds, so a failing/missing-key call leaves the
    counter untouched. Consumption is atomic, but the separate peek and fetch can
    still admit concurrent calls near the ceiling.
    """
    cache = get_cache()
    now = int(time.time())

    if budget.per_minute is not None:
        minute_bucket = now // 60
        used = await cache.get_counter(
            f"ratelimit:{budget.source}:minute:{minute_bucket}"
        )
        if used >= budget.per_minute:
            return False

    if budget.per_day is not None:
        day_bucket = now // 86400
        used = await cache.get_counter(f"ratelimit:{budget.source}:day:{day_bucket}")
        if used >= budget.per_day:
            return False

    return True


async def consume(budget: Budget) -> None:
    """Consume one token in each configured window (minute and/or day)."""
    cache = get_cache()
    now = int(time.time())

    if budget.per_minute is not None:
        minute_bucket = now // 60
        key = f"ratelimit:{budget.source}:minute:{minute_bucket}"
        await cache.incr_counter(key, ttl_seconds=120)

    if budget.per_day is not None:
        day_bucket = now // 86400
        key = f"ratelimit:{budget.source}:day:{day_bucket}"
        await cache.incr_counter(key, ttl_seconds=172800)


async def remaining(budget: Budget) -> dict[str, int | None]:
    cache = get_cache()
    now = int(time.time())
    out: dict[str, int | None] = {}

    if budget.per_minute is not None:
        minute_bucket = now // 60
        used = await cache.get_counter(
            f"ratelimit:{budget.source}:minute:{minute_bucket}"
        )
        out["per_minute"] = max(0, budget.per_minute - used)
    if budget.per_day is not None:
        day_bucket = now // 86400
        used = await cache.get_counter(f"ratelimit:{budget.source}:day:{day_bucket}")
        out["per_day"] = max(0, budget.per_day - used)
    return out
