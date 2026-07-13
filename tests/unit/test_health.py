"""sportiq_health() — registration dedup + quota exposure."""

from __future__ import annotations

import pytest

from sportiq.core import health as health_module
from sportiq.core.health import register_adapter_for_health
from sportiq.core.ratelimit import Budget


class _StubAdapter:
    def __init__(
        self,
        name: str,
        budget: Budget | None = None,
        health_name: str | None = None,
    ) -> None:
        self.name = name
        self.budget = budget
        if health_name is not None:
            self.health_name = health_name

    async def fetch(self, **_kwargs) -> dict:
        return {}

    async def healthcheck(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch):
    monkeypatch.setattr(health_module, "_registered_adapters", [])
    yield


def test_register_adapter_for_health_dedupes_by_name():
    register_adapter_for_health(_StubAdapter("cricapi"))
    register_adapter_for_health(_StubAdapter("cricapi"))
    register_adapter_for_health(_StubAdapter("cricapi"))
    register_adapter_for_health(_StubAdapter("rapidapi_cricbuzz"))

    names = [a.name for a in health_module._registered_adapters]
    assert names == ["cricapi", "rapidapi_cricbuzz"]


def test_register_adapter_for_health_keeps_first_instance():
    first = _StubAdapter("cricapi")
    second = _StubAdapter("cricapi")
    register_adapter_for_health(first)
    register_adapter_for_health(second)

    assert health_module._registered_adapters == [first]


async def test_sportiq_health_includes_quota_per_budgeted_source():
    from sportiq.core.health import get_health_report

    register_adapter_for_health(
        _StubAdapter("cricapi", budget=Budget(source="cricapi", per_day=100))
    )
    register_adapter_for_health(_StubAdapter("static_seed"))

    envelope = await get_health_report()
    quotas = envelope["data"]["quotas"]
    assert "cricapi" in quotas
    assert quotas["cricapi"] == 100  # nothing consumed; full budget remains
    assert "static_seed" not in quotas


async def test_health_names_separate_sports_and_dedupe_shared_provider():
    from sportiq.core.health import get_health_report

    register_adapter_for_health(
        _StubAdapter("static_seed", health_name="football_static_seed")
    )
    register_adapter_for_health(
        _StubAdapter("static_seed", health_name="cricket_static_seed")
    )
    register_adapter_for_health(_StubAdapter("theodds", health_name="theodds"))
    register_adapter_for_health(_StubAdapter("theodds", health_name="theodds"))

    envelope = await get_health_report()
    names = [status["name"] for status in envelope["data"]["adapters"]]
    assert names == ["football_static_seed", "cricket_static_seed", "theodds"]
