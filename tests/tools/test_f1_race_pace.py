"""Tool-layer tests for f1_race_pace_compare."""
from unittest.mock import AsyncMock, MagicMock, patch

from sportiq.core.errors import AllSourcesFailedError
from sportiq.f1.intel_tools import f1_race_pace_compare


def _make_laps_result(base_time: float = 80.0):
    r = MagicMock()
    r.value = {
        "laps": [
            {
                "lap_number": i,
                "compound": "MEDIUM",
                "tyre_life": i,
                "lap_duration": base_time + i * 0.1,
            }
            for i in range(1, 6)
        ]
    }
    r.source = "openf1"
    r.is_stale = False
    r.fallback_used = False
    r.data_age_seconds = 5
    r.duration_ms = 20
    return r


def _make_stints_result():
    r = MagicMock()
    r.value = {"stints": []}
    r.is_stale = False
    r.fallback_used = False
    r.data_age_seconds = 5
    r.duration_ms = 10
    return r


async def test_invalid_same_driver():
    result = await f1_race_pace_compare(session_key=9222, driver_a=1, driver_b=1)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_invalid_session_key():
    result = await f1_race_pace_compare(session_key=0, driver_a=1, driver_b=44)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_all_sources_failed():
    exc = AllSourcesFailedError("all failed", attempts=[])
    with patch(
        "sportiq.f1.intel_tools._fetch_driver_laps",
        new_callable=AsyncMock,
        side_effect=exc,
    ), patch("sportiq.f1.intel_tools.f1_stints_chain") as mock_stints:
        mock_stints.fetch = AsyncMock(return_value=_make_stints_result())
        result = await f1_race_pace_compare(session_key=9222, driver_a=1, driver_b=44)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_valid_returns_envelope():
    laps_a = _make_laps_result(base_time=80.0)
    laps_b = _make_laps_result(base_time=82.0)
    stints = _make_stints_result()

    lap_call_count = 0

    async def fake_fetch_laps(session_key, driver_number):
        nonlocal lap_call_count
        lap_call_count += 1
        return laps_a if driver_number == 1 else laps_b

    with patch(
        "sportiq.f1.intel_tools._fetch_driver_laps",
        side_effect=fake_fetch_laps,
    ), patch("sportiq.f1.intel_tools.f1_stints_chain") as mock_stints:
        mock_stints.fetch = AsyncMock(return_value=stints)
        result = await f1_race_pace_compare(session_key=9222, driver_a=1, driver_b=44)

    assert "data" in result
    assert "meta" in result
    assert result["meta"]["estimated"] is True
    assert "compounds_compared" in result["data"]
    assert "by_compound" in result["data"]
    assert "overall_faster" in result["data"]
