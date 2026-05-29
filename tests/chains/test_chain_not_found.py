"""Chain surfaces NOT_FOUND only when every adapter reported the entity missing."""

from __future__ import annotations

import pytest

from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.fallback import FallbackChain


class _NotFound:
    name = "static_seed"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        raise NotFoundError("no such venue")

    async def healthcheck(self) -> bool:
        return True


class _Boom:
    name = "flaky"
    budget = None

    async def fetch(self, **kwargs) -> dict:
        raise RuntimeError("upstream 500")

    async def healthcheck(self) -> bool:
        return True


def _key(**kwargs) -> str:
    return "nf_test:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


async def test_chain_propagates_not_found_when_all_attempts_not_found():
    chain = FallbackChain(
        name="cricket:nf",
        adapters=[_NotFound()],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=0,
    )
    with pytest.raises(NotFoundError):
        await chain.fetch(venue="atlantis")


async def test_chain_raises_all_sources_failed_when_a_non_not_found_failure_mixes_in():
    chain = FallbackChain(
        name="cricket:nf_mixed",
        adapters=[_NotFound(), _Boom()],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=0,
    )
    with pytest.raises(AllSourcesFailedError):
        await chain.fetch(venue="atlantis")
