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


class _DeadRedis:
    """Stands in for a redis client whose daemon is unreachable. redis.from_url
    is lazy (no I/O at construction), so failures only surface on first use."""

    async def get(self, key):
        raise ConnectionError("connection refused")

    async def set(self, *args, **kwargs):
        raise ConnectionError("connection refused")

    async def ping(self):
        raise ConnectionError("connection refused")


@pytest.mark.asyncio
async def test_downgrades_to_diskcache_when_redis_unreachable():
    """Per CLAUDE.md, an unreachable Redis daemon must downgrade to diskcache —
    not crash every tool at the first cache read."""
    cache = get_cache()
    # Mirror real redis-mode state: redis selected at init, no disk backend yet.
    cache.backend = "redis"
    cache._redis = _DeadRedis()
    cache._disk = None

    await cache.set("k2", {"x": 1}, ttl_seconds=60)  # must not raise
    entry = await cache.get("k2")

    assert cache.backend == "diskcache"
    assert entry is not None
    assert entry.value == {"x": 1}
