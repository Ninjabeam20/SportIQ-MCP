"""FallbackChain[T] — the core resilience primitive.

Every tool routes through one of these. Adapters are tried in order; first
success wins; all failures fall back to stale cache; no stale cache raises
AllSourcesFailedError so the tool can return the error envelope.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from sportiq.core.cache import get_cache
from sportiq.core.errors import AllSourcesFailedError
from sportiq.core.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T")


@runtime_checkable
class Adapter(Protocol, Generic[T]):
    name: str

    async def fetch(self, **kwargs: Any) -> T: ...

    async def healthcheck(self) -> bool: ...


@dataclass
class FallbackResult(Generic[T]):
    value: T
    source: str
    is_stale: bool = False
    data_age_seconds: int = 0
    fallback_used: bool = False
    duration_ms: int = 0
    attempts: list[dict] = field(default_factory=list)


class FallbackChain(Generic[T]):
    def __init__(
        self,
        name: str,
        adapters: list[Adapter[T]],
        cache_key_fn: Callable[..., str],
        fresh_ttl: int,
        stale_ttl: int = 0,
    ) -> None:
        self.name = name
        self.adapters = adapters
        self.cache_key_fn = cache_key_fn
        self.fresh_ttl = fresh_ttl
        self.stale_ttl = stale_ttl

    async def fetch(self, **kwargs: Any) -> FallbackResult[T]:
        started = time.monotonic()
        cache = get_cache()
        key = self.cache_key_fn(**kwargs)

        cached = await cache.get(key)
        if (
            cached is not None
            and self.fresh_ttl > 0
            and cached.age_seconds <= self.fresh_ttl
        ):
            return FallbackResult(
                value=cached.value,
                source=f"cache:{self.name}",
                is_stale=False,
                data_age_seconds=cached.age_seconds,
                fallback_used=False,
                duration_ms=int((time.monotonic() - started) * 1000),
            )

        attempts: list[dict] = []
        for index, adapter in enumerate(self.adapters):
            adapter_started = time.monotonic()
            try:
                value = await adapter.fetch(**kwargs)
            except Exception as e:
                attempts.append(
                    {
                        "name": adapter.name,
                        "status": "error",
                        "error": f"{type(e).__name__}: {e}",
                        "duration_ms": int(
                            (time.monotonic() - adapter_started) * 1000
                        ),
                    }
                )
                log.warning(
                    "chain.adapter.failed",
                    chain=self.name,
                    adapter=adapter.name,
                    error=str(e),
                )
                continue

            attempts.append(
                {
                    "name": adapter.name,
                    "status": "ok",
                    "duration_ms": int((time.monotonic() - adapter_started) * 1000),
                }
            )
            await cache.set(key, value, ttl_seconds=max(self.fresh_ttl, self.stale_ttl))
            return FallbackResult(
                value=value,
                source=adapter.name,
                is_stale=False,
                data_age_seconds=0,
                fallback_used=index > 0,
                duration_ms=int((time.monotonic() - started) * 1000),
                attempts=attempts,
            )

        if cached is not None and self.stale_ttl > 0 and cached.age_seconds <= self.stale_ttl:
            log.info(
                "chain.serving_stale", chain=self.name, age=cached.age_seconds
            )
            return FallbackResult(
                value=cached.value,
                source=f"cache:stale:{self.name}",
                is_stale=True,
                data_age_seconds=cached.age_seconds,
                fallback_used=True,
                duration_ms=int((time.monotonic() - started) * 1000),
                attempts=attempts,
            )

        raise AllSourcesFailedError(
            f"All adapters failed for chain {self.name!r}",
            attempts=attempts,
        )
