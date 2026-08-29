"""FallbackChain consults adapter.budget before each fetch."""

from __future__ import annotations

import asyncio

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackChain
from sportiq.core.ratelimit import Budget, remaining


class _BudgetedOK:
    name = "budgeted"
    budget = Budget(source="chain_budget_test", per_minute=1)

    async def fetch(self, **kwargs) -> dict:
        return {"served_by": "budgeted"}

    async def healthcheck(self) -> bool:
        return True


class _FreeFallback:
    name = "fallback"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        return {"served_by": "fallback"}

    async def healthcheck(self) -> bool:
        return True


class _BudgetedBoom:
    name = "budgeted_boom"
    budget = Budget(source="chain_consume_test", per_day=5)

    async def fetch(self, **kwargs) -> dict:
        raise RuntimeError("boom")

    async def healthcheck(self) -> bool:
        return True


def _key(**kwargs) -> str:
    return "budget_test:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


async def test_chain_skips_budgeted_adapter_when_quota_exhausted():
    chain = FallbackChain(
        name="cricket:budget_test",
        adapters=[_BudgetedOK(), _FreeFallback()],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=0,
    )

    first = await chain.fetch(q="a")
    assert first.source == "budgeted"

    second = await chain.fetch(q="b")
    assert second.source == "fallback"
    skipped = [a for a in second.attempts if a.get("status") == "skipped"]
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "rate_limited"
    assert skipped[0]["name"] == "budgeted"


async def test_chain_does_not_consume_budget_on_failed_fetch():
    chain = FallbackChain(
        name="cricket:consume_test",
        adapters=[_BudgetedBoom(), _FreeFallback()],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=0,
    )

    result = await chain.fetch(q="x")
    assert result.source == "fallback"  # budgeted adapter raised; fell through

    rem = await remaining(Budget(source="chain_consume_test", per_day=5))
    assert rem["per_day"] == 5  # failed fetch burned no token


async def test_concurrent_different_keys_cannot_overspend_budget():
    class _OK:
        name = "ok"
        budget = Budget(source="chain_race_keys", per_day=5)
        calls = 0

        async def fetch(self, **kwargs) -> dict:
            type(self).calls += 1
            await asyncio.sleep(0.01)
            return {"k": kwargs["q"]}

        async def healthcheck(self) -> bool:
            return True

    chain = FallbackChain(
        name="cricket:race_keys",
        adapters=[_OK()],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=0,
    )

    outcomes = await asyncio.gather(
        *(chain.fetch(q=str(i)) for i in range(20)),
        return_exceptions=True,
    )

    successes = [o for o in outcomes if not isinstance(o, BaseException)]
    failures = [o for o in outcomes if isinstance(o, AllSourcesFailedError)]
    assert len(successes) == 5
    assert len(failures) == 15
    assert _OK.calls == 5
    rem = await remaining(Budget(source="chain_race_keys", per_day=5))
    assert rem["per_day"] == 0
