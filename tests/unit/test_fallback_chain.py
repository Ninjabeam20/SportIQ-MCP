"""FallbackChain behavior — the contract every tool depends on."""

from __future__ import annotations

import asyncio
import time

import pytest

from sportiq.core.cache import get_cache
from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.fallback import FallbackChain


class StubAdapter:
    def __init__(self, name: str, response=None, raises: Exception | None = None):
        self.name = name
        self._response = response
        self._raises = raises
        self.call_count = 0

    async def fetch(self, **kwargs):
        self.call_count += 1
        if self._raises is not None:
            raise self._raises
        return self._response

    async def healthcheck(self) -> bool:
        return self._raises is None


def _key(**kwargs) -> str:
    return "test:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))


@pytest.mark.asyncio
async def test_first_adapter_serves_when_healthy():
    primary = StubAdapter("primary", response={"x": 1})
    secondary = StubAdapter("secondary", response={"x": 2})

    chain = FallbackChain(name="t1", adapters=[primary, secondary], cache_key_fn=_key, fresh_ttl=60)
    result = await chain.fetch(q="abc")

    assert result.value == {"x": 1}
    assert result.source == "primary"
    assert result.fallback_used is False
    assert result.is_stale is False
    assert primary.call_count == 1
    assert secondary.call_count == 0


@pytest.mark.asyncio
async def test_falls_back_when_primary_raises():
    primary = StubAdapter("primary", raises=RuntimeError("upstream 500"))
    secondary = StubAdapter("secondary", response={"x": 2})

    chain = FallbackChain(name="t2", adapters=[primary, secondary], cache_key_fn=_key, fresh_ttl=60)
    result = await chain.fetch(q="abc")

    assert result.value == {"x": 2}
    assert result.source == "secondary"
    assert result.fallback_used is True
    assert len(result.attempts) == 2
    assert result.attempts[0]["status"] == "error"
    assert result.attempts[1]["status"] == "ok"


@pytest.mark.asyncio
async def test_cache_hit_skips_adapters():
    primary = StubAdapter("primary", response={"x": 1})
    chain = FallbackChain(name="t3", adapters=[primary], cache_key_fn=_key, fresh_ttl=60)

    first = await chain.fetch(q="same")
    second = await chain.fetch(q="same")

    assert first.source == "primary"
    assert second.source.startswith("cache:")
    assert primary.call_count == 1


@pytest.mark.asyncio
async def test_serves_stale_when_all_adapters_fail():
    primary = StubAdapter("primary", response={"x": 1})
    chain = FallbackChain(
        name="t4",
        adapters=[primary],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=3600,
    )

    await chain.fetch(q="stale-test")

    primary._raises = RuntimeError("now broken")
    primary._response = None

    result = await chain.fetch(q="stale-test")
    assert result.value == {"x": 1}
    assert result.is_stale is True
    assert result.fallback_used is True
    assert result.source.startswith("cache:stale:")


@pytest.mark.asyncio
async def test_concurrent_identical_fetches_hit_upstream_once():
    """Cache-stampede guard: N concurrent misses for the same key must result in
    ONE adapter call; the rest serve from the cache the first call populated.
    On the shared hosted instance this protects both latency and API quota."""

    class SlowAdapter(StubAdapter):
        async def fetch(self, **kwargs):
            self.call_count += 1
            await asyncio.sleep(0.05)
            return self._response

    adapter = SlowAdapter("slow", response={"x": 1})
    chain = FallbackChain(name="t6", adapters=[adapter], cache_key_fn=_key, fresh_ttl=60)

    results = await asyncio.gather(*[chain.fetch(q="same") for _ in range(5)])

    assert adapter.call_count == 1
    assert all(r.value == {"x": 1} for r in results)


@pytest.mark.asyncio
async def test_hanging_adapter_times_out_and_chain_falls_back():
    """A hung upstream must not stall the whole chain: the walk has a time
    budget, a too-slow adapter is recorded as an error attempt, and the next
    adapter still gets its turn."""

    class HangingAdapter(StubAdapter):
        async def fetch(self, **kwargs):
            self.call_count += 1
            await asyncio.sleep(5)
            return self._response

    hanging = HangingAdapter("hanging", response={"x": 1})
    fast = StubAdapter("fast", response={"x": 2})
    chain = FallbackChain(
        name="t7",
        adapters=[hanging, fast],
        cache_key_fn=_key,
        fresh_ttl=60,
        time_budget_s=0.1,
    )

    result = await chain.fetch(q="hung-upstream")

    assert result.value == {"x": 2}
    assert result.source == "fast"
    assert result.attempts[0]["status"] == "error"
    assert "Timeout" in result.attempts[0]["error"]


@pytest.mark.asyncio
async def test_raises_when_all_fail_and_no_cache():
    primary = StubAdapter("primary", raises=RuntimeError("boom"))
    secondary = StubAdapter("secondary", raises=RuntimeError("also boom"))

    chain = FallbackChain(
        name="t5",
        adapters=[primary, secondary],
        cache_key_fn=_key,
        fresh_ttl=60,
    )

    with pytest.raises(AllSourcesFailedError) as excinfo:
        await chain.fetch(q="no-cache-here")

    assert len(excinfo.value.attempts) == 2
    assert all(a["status"] == "error" for a in excinfo.value.attempts)


class SleepyAdapter(StubAdapter):
    """Returns its response after ``delay`` seconds (0 = immediately)."""

    def __init__(self, name: str, response=None, delay: float = 0.0):
        super().__init__(name, response=response)
        self.delay = delay

    async def fetch(self, **kwargs):
        self.call_count += 1
        await asyncio.sleep(self.delay)
        return self._response


@pytest.mark.asyncio
async def test_fallback_chain_total_budget_caps_serial_adapters():
    first = SleepyAdapter("first", response={"x": 1}, delay=1)
    second = SleepyAdapter("second", response={"x": 2}, delay=1)
    chain = FallbackChain(
        name="t8",
        adapters=[first, second],
        cache_key_fn=_key,
        fresh_ttl=60,
        time_budget_s=1,
        total_budget_s=0.3,
    )

    started = time.perf_counter()
    with pytest.raises(AllSourcesFailedError) as excinfo:
        await chain.fetch(q="slow-walk")
    elapsed = time.perf_counter() - started

    assert elapsed < 0.6
    assert second.call_count == 0
    skipped = excinfo.value.attempts[1]
    assert skipped["name"] == "second"
    assert skipped["status"] == "skipped"
    assert skipped["reason"] == "chain_deadline"


@pytest.mark.asyncio
async def test_fallback_chain_serves_stale_after_total_budget_expires():
    first = SleepyAdapter("first", response={"x": 1})
    second = SleepyAdapter("second", response={"x": 2})
    chain = FallbackChain(
        name="t9",
        adapters=[first, second],
        cache_key_fn=_key,
        fresh_ttl=0,
        stale_ttl=3600,
        time_budget_s=1,
        total_budget_s=0.3,
    )
    await chain.fetch(q="stale-budget")  # seeds the cache from "first"

    first.delay = second.delay = 1
    result = await chain.fetch(q="stale-budget")

    assert result.value == {"x": 1}
    assert result.is_stale is True
    assert any(a.get("reason") == "chain_deadline" for a in result.attempts)


@pytest.mark.asyncio
async def test_fallback_chain_returns_value_when_cache_set_raises(monkeypatch):
    async def _broken_set(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(get_cache(), "set", _broken_set)
    primary = StubAdapter("primary", response={"x": 1})
    chain = FallbackChain(name="t10", adapters=[primary], cache_key_fn=_key, fresh_ttl=60)

    result = await chain.fetch(q="write-fails")

    assert result.value == {"x": 1}
    assert result.source == "primary"


@pytest.mark.asyncio
async def test_fallback_chain_treats_cache_get_error_as_miss(monkeypatch):
    async def _broken_get(*args, **kwargs):
        raise OSError("database is locked")

    monkeypatch.setattr(get_cache(), "get", _broken_get)
    primary = StubAdapter("primary", response={"x": 1})
    chain = FallbackChain(name="t11", adapters=[primary], cache_key_fn=_key, fresh_ttl=60)

    result = await chain.fetch(q="read-fails")

    assert primary.call_count == 1
    assert result.value == {"x": 1}
