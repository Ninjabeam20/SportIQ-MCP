"""sportiq_health — first-class meta-tool.

Reports cache backend, per-adapter healthcheck, remaining quotas. Use in chat
(*"is anything down?"*) and from CI smoke tests.

In Phase 0 we have no adapters yet, so the report is just cache + version.
Sport modules append their adapters via `register_adapter_for_health()`.
"""

from __future__ import annotations

from sportiq import __version__
from sportiq.core.cache import get_cache
from sportiq.core.ratelimit import remaining
from sportiq.core.schemas import AdapterStatus, HealthReport
from sportiq.core.tool_response import Envelope

_registered_adapters: list = []


def register_adapter_for_health(adapter) -> None:
    """Sport modules call this when they construct their chains.

    Deduped by ``adapter.name``: chains often instantiate several adapter
    classes that share the same upstream identity (e.g. all the CricAPI
    flavours), but ``sportiq_health()`` should report each upstream once.
    The first registration wins — chains should register their primary /
    most-representative healthcheck first.
    """
    if any(existing.name == adapter.name for existing in _registered_adapters):
        return
    _registered_adapters.append(adapter)


async def get_health_report() -> dict:
    """Build the {data, meta} health envelope. Used by the MCP tool and tests."""
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

    quotas: dict[str, int] = {}
    seen_sources: set[str] = set()
    for adapter in _registered_adapters:
        budget = getattr(adapter, "budget", None)
        if budget is None or budget.source in seen_sources:
            continue
        seen_sources.add(budget.source)
        remaining_dict = await remaining(budget)
        if "per_day" in remaining_dict and remaining_dict["per_day"] is not None:
            quotas[budget.source] = remaining_dict["per_day"]
        elif "per_minute" in remaining_dict and remaining_dict["per_minute"] is not None:
            quotas[budget.source] = remaining_dict["per_minute"]

    report = HealthReport(
        cache_backend=cache.backend,
        cache_ok=cache_ok,
        adapters=adapter_statuses,
        quotas=quotas,
    )
    return {"data": report.model_dump(), "meta": {"version": __version__}}


def register_health_tool(mcp) -> None:
    """Attach sportiq_health() to the FastMCP instance."""
    from sportiq.core.tool_meta import READ_ONLY

    @mcp.tool(annotations=READ_ONLY)
    async def sportiq_health() -> Envelope:
        """Report cache backend, per-adapter healthcheck, and quota status.

        Returns:
            HealthReport-shaped dict with `cache_backend`, `cache_ok`,
            `adapters` (per-source ok/detail), and `quotas`.
        """
        return await get_health_report()
