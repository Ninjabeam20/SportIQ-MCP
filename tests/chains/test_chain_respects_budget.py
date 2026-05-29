"""FallbackChain consults adapter.budget before each fetch."""

from __future__ import annotations

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
