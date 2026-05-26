from typing import Literal

from pydantic import BaseModel


class Meta(BaseModel):
    source: str
    is_stale: bool = False
    data_age_seconds: int = 0
    fallback_used: bool = False
    duration_ms: int = 0


class AdapterStatus(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class HealthReport(BaseModel):
    cache_backend: Literal["redis", "diskcache"]
    cache_ok: bool
    adapters: list[AdapterStatus]
    quotas: dict[str, int] = {}
