"""Cache backend selects diskcache when REDIS_URL is unset."""

import pytest

from sportiq.core.cache import get_cache


@pytest.mark.asyncio
async def test_backend_is_diskcache_without_redis_url():
    cache = get_cache()
    assert cache.backend == "diskcache"


@pytest.mark.asyncio
async def test_set_then_get_roundtrip():
    cache = get_cache()
    await cache.set("k", {"hello": "world"}, ttl_seconds=60)
    entry = await cache.get("k")
    assert entry is not None
    assert entry.value == {"hello": "world"}
    assert entry.age_seconds >= 0


@pytest.mark.asyncio
async def test_get_returns_none_for_missing_key():
    cache = get_cache()
    assert await cache.get("never-set") is None


@pytest.mark.asyncio
async def test_healthcheck_passes_on_diskcache():
    cache = get_cache()
    assert await cache.healthcheck() is True
