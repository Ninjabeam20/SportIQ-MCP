"""Health tool tests — assert report shape and required fields.

``get_health_report()`` awaits ``healthcheck()`` on every registered adapter, and
some real healthchecks make a live HTTP call when their key is set. These tests
stub ``_registered_adapters`` with inert fakes so the report-building logic is
exercised deterministically, with no network and no dependence on import order.
"""
from __future__ import annotations

import pytest

from sportiq.core import health
from sportiq.core.ratelimit import Budget


class _StubAdapter:
    """Inert adapter: async healthcheck, optional budget. No I/O."""

    def __init__(self, name: str, ok: bool, budget: Budget | None = None):
        self.name = name
        self._ok = ok
        if budget is not None:
            self.budget = budget

    async def healthcheck(self) -> bool:
        return self._ok


@pytest.fixture
def stub_adapters(monkeypatch: pytest.MonkeyPatch):
    """Replace the real registry with two inert stubs (one carries a budget)."""
    adapters = [
        _StubAdapter("stub_ok", ok=True, budget=Budget(source="stub_ok", per_day=100)),
        _StubAdapter("stub_down", ok=False),
    ]
    monkeypatch.setattr(health, "_registered_adapters", adapters)
    return adapters


async def test_health_report_returns_data_meta_shape(stub_adapters):
    result = await health.get_health_report()
    assert "data" in result
    assert "meta" in result


async def test_health_report_data_has_cache_fields(stub_adapters):
    result = await health.get_health_report()
    data = result["data"]
    assert "cache_backend" in data
    assert "cache_ok" in data
    assert "adapters" in data
    assert "quotas" in data


async def test_health_report_reports_per_adapter_status(stub_adapters):
    result = await health.get_health_report()
    statuses = {a["name"]: a["ok"] for a in result["data"]["adapters"]}
    assert statuses == {"stub_ok": True, "stub_down": False}


async def test_health_report_quotas_only_from_budgeted_adapters(stub_adapters):
    result = await health.get_health_report()
    quotas = result["data"]["quotas"]
    assert quotas == {"stub_ok": 100}


async def test_health_report_meta_has_version(stub_adapters):
    result = await health.get_health_report()
    assert "version" in result["meta"]
    assert isinstance(result["meta"]["version"], str)
