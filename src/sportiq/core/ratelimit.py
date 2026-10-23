"""Per-source token bucket. Counters stored in the unified cache.

Budget math assumes a single process: the Dell Compose stack keeps one
``sportiq`` replica until counters live in shared Redis.
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


@dataclass(frozen=True)
class Reservation:
    """The exact window counters one :func:`reserve_window` call incremented."""

    minute_key: str | None
    day_key: str | None


async def reserve_window(budget: Budget) -> Reservation | None:
    """Atomically take one token in each configured window, or take none.

    Returns the :class:`Reservation` (the window keys charged) if the caller may
    proceed to fetch, else None with the counters unchanged. Pass it to
    :func:`refund` if the fetch fails, so the refund hits the windows that were
    charged even when the fetch ends in a later minute or UTC day.
    """
    cache = get_cache()
    now = int(time.time())
    minute_key: str | None = None
    day_key: str | None = None

    if budget.per_minute is not None:
        minute_key = _minute_key(budget.source, now)
        taken = await cache.incr_counter_if_below(minute_key, budget.per_minute, ttl_seconds=120)
        if taken is None:
            return None

    if budget.per_day is not None:
        day_key = _day_key(budget.source, now)
        taken = await cache.incr_counter_if_below(day_key, budget.per_day, ttl_seconds=172800)
        if taken is None:
            if minute_key is not None:
                await cache.decr_counter(minute_key)
            return None

    return Reservation(minute_key=minute_key, day_key=day_key)


async def reserve(budget: Budget) -> bool:
    """Boolean form of :func:`reserve_window` (True = a token was taken)."""
    return await reserve_window(budget) is not None


async def refund(budget: Budget, reservation: Reservation | None = None) -> None:
    """Give back one token in each configured window after a failed fetch.

    With ``reservation`` the exact charged windows are refunded; without it the
    current windows are (only correct if no minute/day boundary was crossed).
    """
    cache = get_cache()
    if reservation is not None:
        for key in (reservation.minute_key, reservation.day_key):
            if key is not None:
                await cache.decr_counter(key)
        return
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
