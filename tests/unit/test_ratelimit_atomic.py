import asyncio

import pytest

from sportiq.core.ratelimit import Budget, consume, remaining


@pytest.mark.asyncio
async def test_consume_preserves_concurrent_increments():
    budget = Budget(source="atomic-test", per_day=100)

    await asyncio.gather(*(consume(budget) for _ in range(50)))

    assert (await remaining(budget))["per_day"] == 50
