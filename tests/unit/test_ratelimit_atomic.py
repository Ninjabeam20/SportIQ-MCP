import asyncio

import pytest

from sportiq.core.ratelimit import Budget, consume, refund, remaining, reserve


@pytest.mark.asyncio
async def test_consume_preserves_concurrent_increments():
    budget = Budget(source="atomic-test", per_day=100)

    await asyncio.gather(*(consume(budget) for _ in range(50)))

    assert (await remaining(budget))["per_day"] == 50


@pytest.mark.asyncio
async def test_reserve_rejects_when_day_budget_exhausted():
    budget = Budget(source="reserve-cap-test", per_day=2)

    assert await reserve(budget) is True
    assert await reserve(budget) is True
    assert await reserve(budget) is False
    assert (await remaining(budget))["per_day"] == 0


@pytest.mark.asyncio
async def test_refund_restores_token():
    budget = Budget(source="refund-test", per_day=1)

    assert await reserve(budget) is True
    assert await reserve(budget) is False
    await refund(budget)
    assert await reserve(budget) is True


@pytest.mark.asyncio
async def test_concurrent_reserve_does_not_exceed_limit():
    budget = Budget(source="race-reserve-test", per_day=10)

    results = await asyncio.gather(*(reserve(budget) for _ in range(40)))

    assert sum(results) == 10
    assert (await remaining(budget))["per_day"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("per", "t0", "t1"),
    [("per_minute", 59, 60), ("per_day", 86_399, 86_400)],
)
async def test_refund_after_window_rollover_returns_the_charged_window(monkeypatch, per, t0, t1):
    # Review R2: reserve in window N, fail in N+1 after another caller reserved
    # N+1 → the refund must go back to N, not free a slot in the full N+1.
    from sportiq.core import ratelimit
    from sportiq.core.ratelimit import reserve_window

    budget = Budget(source=f"rollover-{per}", **{per: 1})
    clock = {"now": t0}
    monkeypatch.setattr(ratelimit.time, "time", lambda: clock["now"])

    first = await reserve_window(budget)
    assert first is not None
    clock["now"] = t1
    assert await reserve(budget) is True  # the new window's only slot
    await refund(budget, first)  # first fetch failed after the rollover
    assert await reserve(budget) is False  # new window still full
