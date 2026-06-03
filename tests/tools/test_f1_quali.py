"""Tool-layer tests for f1_qualifying_analysis."""
from unittest.mock import AsyncMock, MagicMock, patch

from sportiq.f1.intel_tools import f1_qualifying_analysis


async def test_invalid_session_key():
    result = await f1_qualifying_analysis(0)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_all_sources_failed():
    from sportiq.core.errors import AllSourcesFailedError

    with patch("sportiq.f1.intel_tools.f1_drivers_chain") as mock_chain:
        mock_chain.fetch = AsyncMock(side_effect=AllSourcesFailedError("all failed", attempts=[]))
        result = await f1_qualifying_analysis(9222)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_valid_returns_envelope():
    mock_drivers = MagicMock()
    mock_drivers.value = {
        "drivers": [{"driver_number": 1, "full_name": "Max V", "team_name": "RBR"}]
    }
    mock_drivers.source = "openf1"
    mock_drivers.is_stale = False
    mock_drivers.fallback_used = False
    mock_drivers.data_age_seconds = 5
    mock_drivers.duration_ms = 20

    mock_laps = MagicMock()
    mock_laps.value = {"laps": [{"driver_number": 1, "lap_duration": 89.3, "lap_number": 1}]}
    mock_laps.is_stale = False
    mock_laps.fallback_used = False
    mock_laps.data_age_seconds = 5
    mock_laps.duration_ms = 10

    with patch("sportiq.f1.intel_tools.f1_drivers_chain") as md, patch(
        "sportiq.f1.intel_tools._fetch_driver_laps", new_callable=AsyncMock
    ) as ml:
        md.fetch = AsyncMock(return_value=mock_drivers)
        ml.return_value = mock_laps
        result = await f1_qualifying_analysis(9222)

    assert "data" in result
    assert result["meta"]["estimated"] is True
    assert "grid" in result["data"]
    assert "pole_time_s" in result["data"]
    assert result["data"]["pole_time_s"] == 89.3
    assert result["data"]["drivers_analysed"] == 1
    assert result["data"]["grid"][0]["position"] == 1


async def test_no_laps_returns_empty_grid():
    mock_drivers = MagicMock()
    mock_drivers.value = {
        "drivers": [{"driver_number": 1, "full_name": "Max V", "team_name": "RBR"}]
    }
    mock_drivers.source = "openf1"
    mock_drivers.is_stale = False
    mock_drivers.fallback_used = False
    mock_drivers.data_age_seconds = 0
    mock_drivers.duration_ms = 5

    with patch("sportiq.f1.intel_tools.f1_drivers_chain") as md, patch(
        "sportiq.f1.intel_tools._fetch_driver_laps", new_callable=AsyncMock
    ) as ml:
        md.fetch = AsyncMock(return_value=mock_drivers)
        ml.side_effect = Exception("no laps")
        result = await f1_qualifying_analysis(9222)

    assert "data" in result
    assert result["data"]["grid"] == []
    assert result["data"]["pole_time_s"] is None
