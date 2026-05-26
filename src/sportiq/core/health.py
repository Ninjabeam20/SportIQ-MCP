"""sportiq_health — first-class meta-tool.

Reports cache backend, per-adapter healthcheck, remaining quotas. Use in chat
(*"is anything down?"*) and from CI smoke tests.

In Phase 0 we have no adapters yet, so the report is just cache + version.
Sport modules append their adapters via `register_adapter_for_health()`.
"""

from __future__ import annotations

from sportiq import __version__
from sportiq.core.cache import get_cache
from sportiq.core.schemas import AdapterStatus, HealthReport

_registered_adapters: list = []


def register_adapter_for_health(adapter) -> None:
    """Sport modules call this when they construct their chains."""
    _registered_adapters.append(adapter)


def register_health_tool(mcp) -> None:
    """Attach sportiq_health() to the FastMCP instance."""

    @mcp.tool()
    async def sportiq_health() -> dict:
        """Report cache backend, per-adapter healthcheck, and quota status.

        Returns:
            HealthReport-shaped dict with `cache_backend`, `cache_ok`,
            `adapters` (per-source ok/detail), and `quotas`.
        """
        cache = get_cache()
        cache_ok = await cache.healthcheck()

        adapter_statuses: list[AdapterStatus] = []
        for adapter in _registered_adapters:
            try:
                ok = await adapter.healthcheck()
                adapter_statuses.append(
                    AdapterStatus(name=adapter.name, ok=ok, detail=None)
                )
            except Exception as e:
                adapter_statuses.append(
                    AdapterStatus(name=adapter.name, ok=False, detail=str(e))
                )

        report = HealthReport(
            cache_backend=cache.backend,
            cache_ok=cache_ok,
            adapters=adapter_statuses,
            quotas={},
        )
        return {"data": report.model_dump(), "meta": {"version": __version__}}
