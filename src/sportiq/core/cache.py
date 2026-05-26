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

        settings.diskcache_dir.mkdir(parents=True, exist_ok=True)
        self._disk = diskcache.Cache(str(settings.diskcache_dir))
        self.backend = "diskcache"
        log.info(
            "cache.backend.selected", backend="diskcache", dir=str(settings.diskcache_dir)
        )

    async def get(self, key: str) -> CachedEntry | None:
        if self.backend == "redis":
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return _decode(raw)
        raw = self._disk.get(key)
        if raw is None:
            return None
        return _decode(raw)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        encoded = _encode(value)
        if self.backend == "redis":
            await self._redis.set(key, encoded, ex=ttl_seconds)
        else:
            self._disk.set(key, encoded, expire=ttl_seconds)

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


def _decode(raw: str) -> CachedEntry:
    import json

    payload = json.loads(raw)
    return CachedEntry(value=payload["value"], stored_at=payload["stored_at"])


_cache_singleton: Cache | None = None


def get_cache() -> Cache:
    global _cache_singleton
    if _cache_singleton is None:
        _cache_singleton = Cache()
    return _cache_singleton
