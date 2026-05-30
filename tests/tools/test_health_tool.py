"""Health tool tests — assert report shape and required fields."""
from __future__ import annotations


async def test_health_report_returns_data_meta_shape():
    from sportiq.core.health import get_health_report

    result = await get_health_report()
    assert "data" in result
    assert "meta" in result


async def test_health_report_data_has_cache_fields():
    from sportiq.core.health import get_health_report

    result = await get_health_report()
    data = result["data"]
    assert "cache_backend" in data
    assert "cache_ok" in data
    assert "adapters" in data
    assert "quotas" in data


async def test_health_report_meta_has_version():
    from sportiq.core.health import get_health_report

    result = await get_health_report()
    assert "version" in result["meta"]
    assert isinstance(result["meta"]["version"], str)
