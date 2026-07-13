"""Unified cache: Redis primary, diskcache automatic fallback.

Per CLAUDE.md hard rule: local dev assumes diskcache. We never crash if
Redis is unavailable — we silently downgrade. `sportiq_health()` reports
the active backend so the caller knows which one served them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

import diskcache

from sportiq.config import settings
from sportiq.core.logging import get_logger

log = get_logger(__name__)


@dataclass
class CachedEntry:
    value: Any
    stored_at: float

    @property
    def age_seconds(self) -> int:
        return int(time.time() - self.stored_at)


class Cache:
    """Thin uniform interface over Redis or diskcache.

    Stored values are JSON-serializable Python objects wrapped with a stored_at
    timestamp so we can compute age and stale-eligibility.
    """

    def __init__(self) -> None:
        self.backend: Literal["redis", "diskcache"] = "diskcache"
        self._redis = None
        self._disk: diskcache.Cache | None = None
        self._init_backend()

    def _init_backend(self) -> None:
        if settings.redis_url:
            try:
                import redis.asyncio as redis_async

                self._redis = redis_async.from_url(
                    settings.redis_url, decode_responses=True
                )
                self.backend = "redis"
                log.info("cache.backend.selected", backend="redis")
                return
            except Exception as e:
                log.warning(
                    "cache.redis.unavailable_falling_back_to_diskcache",
                    error=str(e),
                )

        self._init_disk()

    def _init_disk(self) -> None:
        settings.diskcache_dir.mkdir(parents=True, exist_ok=True)
        self._disk = diskcache.Cache(str(settings.diskcache_dir))
        self.backend = "diskcache"
        log.info(
            "cache.backend.selected", backend="diskcache", dir=str(settings.diskcache_dir)
        )

    def _downgrade_to_disk(self, error: Exception) -> None:
        """redis.from_url is lazy (no I/O), so an unreachable daemon only fails
        at first use. Downgrade permanently for this process instead of letting
        the error crash every tool (the CLAUDE.md cache contract)."""
        log.warning(
            "cache.redis.unreachable_falling_back_to_diskcache", error=str(error)
        )
        self._init_disk()

    async def get(self, key: str) -> CachedEntry | None:
        if self.backend == "redis":
            try:
                raw = await self._redis.get(key)
            except Exception as e:
                self._downgrade_to_disk(e)
            else:
                if raw is None:
                    return None
                if raw.strip().lstrip("-").isdigit():
                    return None
                try:
                    return _decode(raw)
                except (KeyError, TypeError, ValueError) as e:
                    log.warning(
                        "cache.entry.corrupt",
                        key=key,
                        backend=self.backend,
                        error=type(e).__name__,
                    )
                    await self.delete(key)
                    return None
        raw = self._disk.get(key)
        if raw is None:
            return None
        if not isinstance(raw, str):
            return None
        try:
            return _decode(raw)
        except (KeyError, TypeError, ValueError) as e:
            log.warning(
                "cache.entry.corrupt",
                key=key,
                backend=self.backend,
                error=type(e).__name__,
            )
            await self.delete(key)
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        encoded = _encode(value)
        if self.backend == "redis":
            try:
                await self._redis.set(key, encoded, ex=ttl_seconds)
                return
            except Exception as e:
                self._downgrade_to_disk(e)
        self._disk.set(key, encoded, expire=ttl_seconds)

    async def get_counter(self, key: str) -> int:
        """Return a raw integer counter, separate from wrapped cache entries."""
        if self.backend == "redis":
            try:
                raw = await self._redis.get(key)
            except Exception as e:
                self._downgrade_to_disk(e)
            else:
                try:
                    return int(raw) if raw is not None else 0
                except (TypeError, ValueError):
                    return 0
        raw = self._disk.get(key)
        return int(raw) if isinstance(raw, int) and not isinstance(raw, bool) else 0

    async def incr_counter(self, key: str, ttl_seconds: int) -> int:
        """Atomically increment a raw counter and set expiry on first write."""
        if self.backend == "redis":
            try:
                value = await self._redis.eval(
                    "local v=redis.call('INCR',KEYS[1]); "
                    "if v==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return v",
                    1,
                    key,
                    ttl_seconds,
                )
                return int(value)
            except Exception as e:
                self._downgrade_to_disk(e)
        with self._disk.transact():
            value = self._disk.incr(key, delta=1, default=0)
            if value == 1:
                self._disk.expire(key, ttl_seconds)
        return int(value)

    async def delete(self, key: str) -> None:
        if self.backend == "redis":
            try:
                await self._redis.delete(key)
                return
            except Exception as e:
                self._downgrade_to_disk(e)
        self._disk.delete(key)

    async def close(self) -> None:
        """Release backend resources; a closed instance must not be reused."""
        redis_client = self._redis
        disk_cache = self._disk
        self._redis = None
        self._disk = None
        if redis_client is not None:
            close_redis = getattr(redis_client, "aclose", None)
            if close_redis is not None:
                try:
                    await close_redis()
                except Exception as e:
                    log.warning("cache.redis.close_failed", error=type(e).__name__)
        if disk_cache is not None:
            disk_cache.close()

    async def healthcheck(self) -> bool:
        try:
            if self.backend == "redis":
                pong = await self._redis.ping()
                return bool(pong)
            self._disk.set("__health__", "ok", expire=5)
            return self._disk.get("__health__") == "ok"
        except Exception as e:
            log.warning("cache.healthcheck.failed", backend=self.backend, error=str(e))
            return False


def _encode(value: Any) -> str:
    import json

    return json.dumps({"value": value, "stored_at": time.time()})


def _decode(raw: str) -> CachedEntry | None:
    import json

    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("cache payload must be an object")
    stored_at = payload["stored_at"]
    if not isinstance(stored_at, (int, float)):
        raise TypeError("cache stored_at must be numeric")
    return CachedEntry(value=payload["value"], stored_at=stored_at)


_cache_singleton: Cache | None = None


def get_cache() -> Cache:
    global _cache_singleton
    if _cache_singleton is None:
        _cache_singleton = Cache()
    return _cache_singleton


async def close_cache() -> None:
    global _cache_singleton
    cache = _cache_singleton
    _cache_singleton = None
    if cache is not None:
        await cache.close()
