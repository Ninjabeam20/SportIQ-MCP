"""Per-source token bucket. Counters stored in the unified cache.

Budget math assumes a single process: Cloud Run must keep --max-instances=1
until counters live in shared Redis.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from sportiq.core.cache import get_cache


@dataclass(frozen=True)
class Budget:
    source: str
    per_minute: int | None = None
    per_day: int | None = None


def _minute_key(source: str, now: int) -> str:
    return f"ratelimit:{source}:minute:{now // 60}"


def _day_key(source: str, now: int) -> str:
    return f"ratelimit:{source}:day:{now // 86400}"


async def has_budget(budget: Budget) -> bool:
    """Peek: return True if a request is within budget. Does NOT consume.

    Prefer :func:`reserve` for admission — a separate peek and fetch can still
    admit concurrent calls near the ceiling. Kept for health/diagnostics.
    """
    cache = get_cache()
    now = int(time.time())

    if budget.per_minute is not None:
        used = await cache.get_counter(_minute_key(budget.source, now))
        if used >= budget.per_minute:
            return False

    if budget.per_day is not None:
        used = await cache.get_counter(_day_key(budget.source, now))
        if used >= budget.per_day:
            return False

    return True


async def reserve(budget: Budget) -> bool:
    """Atomically take one token in each configured window, or take none.

    Returns True if the caller may proceed to fetch. On False the counters are
    unchanged. Pair with :func:`refund` if the subsequent fetch fails so failed
    / missing-key calls still burn no quota.
    """
    cache = get_cache()
    now = int(time.time())
    minute_key: str | None = None

    if budget.per_minute is not None:
        minute_key = _minute_key(budget.source, now)
        taken = await cache.incr_counter_if_below(minute_key, budget.per_minute, ttl_seconds=120)
        if taken is None:
            return False

    if budget.per_day is not None:
        taken = await cache.incr_counter_if_below(
            _day_key(budget.source, now), budget.per_day, ttl_seconds=172800
        )
        if taken is None:
            if minute_key is not None:
                await cache.decr_counter(minute_key)
            return False

    return True


async def refund(budget: Budget) -> None:
    """Give back one token in each configured window after a failed fetch."""
    cache = get_cache()
    now = int(time.time())
    if budget.per_minute is not None:
        await cache.decr_counter(_minute_key(budget.source, now))
    if budget.per_day is not None:
        await cache.decr_counter(_day_key(budget.source, now))


async def consume(budget: Budget) -> None:
    """Unconditionally increment each configured window (tests / diagnostics)."""
    cache = get_cache()
    now = int(time.time())

    if budget.per_minute is not None:
        await cache.incr_counter(_minute_key(budget.source, now), ttl_seconds=120)

    if budget.per_day is not None:
        await cache.incr_counter(_day_key(budget.source, now), ttl_seconds=172800)


async def remaining(budget: Budget) -> dict[str, int | None]:
    cache = get_cache()
    now = int(time.time())
    out: dict[str, int | None] = {}

    if budget.per_minute is not None:
        used = await cache.get_counter(_minute_key(budget.source, now))
        out["per_minute"] = max(0, budget.per_minute - used)
    if budget.per_day is not None:
        used = await cache.get_counter(_day_key(budget.source, now))
        out["per_day"] = max(0, budget.per_day - used)
    return out
