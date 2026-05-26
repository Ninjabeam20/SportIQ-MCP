"""FallbackChain behavior for cricket chains — all adapters stubbed."""

from __future__ import annotations

import pytest

from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackChain


class _OK:
    def __init__(self, name: str, payload: dict):
        self.name = name
        self._payload = payload

    async def fetch(self, **kwargs) -> dict:
        return self._payload

    async def healthcheck(self) -> bool:
        return True


class _Fail:
    def __init__(self, name: str, exc: Exception | None = None):
        self.name = name
        self._exc = exc or RuntimeError(f"{name} unavailable")

    async def fetch(self, **kwargs) -> dict:
        raise self._exc

    async def healthcheck(self) -> bool:
        return False


def _key(**kwargs) -> str:
    return "cricket:test:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


async def test_live_score_chain_first_adapter_wins():
    chain = FallbackChain(
        name="cricket:live_score",
        adapters=[_OK("cricapi", {"matches": [{"id": "m1"}]}), _Fail("ndtv")],
        cache_key_fn=_key,
        fresh_ttl=30,
        stale_ttl=300,
    )
    result = await chain.fetch()
    assert result.source == "cricapi"
    assert result.value["matches"][0]["id"] == "m1"
    assert result.fallback_used is False


async def test_live_score_chain_falls_back_on_primary_failure():
    chain = FallbackChain(
        name="cricket:live_score",
        adapters=[_Fail("cricapi"), _OK("ndtv", {"matches": [{"raw": "IND vs AUS"}]})],
        cache_key_fn=_key,
        fresh_ttl=30,
        stale_ttl=300,
    )
    result = await chain.fetch()
    assert result.source == "ndtv"
    assert result.fallback_used is True


async def test_squad_chain_falls_through_to_static_seed():
    chain = FallbackChain(
        name="cricket:squad",
        adapters=[
            _Fail("cricapi"),
            _Fail("cricsheet"),
            _OK("static_seed", {"players": [{"name": "Rohit Sharma"}], "team": "MI"}),
        ],
        cache_key_fn=_key,
        fresh_ttl=43200,
        stale_ttl=259200,
    )
    result = await chain.fetch(team="MI")
    assert result.source == "static_seed"
    assert result.fallback_used is True
    assert result.value["players"][0]["name"] == "Rohit Sharma"


async def test_chain_raises_when_all_fail_and_no_cache():
    chain = FallbackChain(
        name="cricket:live_score",
        adapters=[_Fail("cricapi"), _Fail("ndtv"), _Fail("cricbuzz"), _Fail("rapidapi")],
        cache_key_fn=_key,
        fresh_ttl=30,
    )
    with pytest.raises(AllSourcesFailedError) as exc:
        await chain.fetch()
    assert len(exc.value.attempts) == 4
    assert all(a["status"] == "error" for a in exc.value.attempts)


async def test_chain_serves_stale_when_all_fail():
    chain = FallbackChain(
        name="cricket:live_score",
        adapters=[_OK("cricapi", {"matches": [{"id": "stale"}]})],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=3600,
    )
    await chain.fetch()

    chain.adapters = [_Fail("cricapi")]
    result = await chain.fetch()
    assert result.is_stale is True
    assert result.source.startswith("cache:stale:")
    assert result.value["matches"][0]["id"] == "stale"
