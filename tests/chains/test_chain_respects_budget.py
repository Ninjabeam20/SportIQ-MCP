"""FallbackChain consults adapter.budget before each fetch."""

from __future__ import annotations

from sportiq.core.fallback import FallbackChain
from sportiq.core.ratelimit import Budget


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
