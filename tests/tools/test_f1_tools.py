"""F1 RAW tool envelope + error-envelope tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sportiq.core.errors import AllSourcesFailedError, NotFoundError
from sportiq.core.fallback import FallbackResult


def _fr(value, source="openf1"):
    return FallbackResult(
        value=value,
        source=source,
        is_stale=False,
        data_age_seconds=0,
        fallback_used=False,
        duration_ms=1,
    )


async def test_f1_get_sessions_returns_data_envelope():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_sessions_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr({"sessions": [{"session_key": 9877}]}))
        result = await tools.f1_get_sessions(year=2025)
    assert "data" in result
    assert "meta" in result
    assert result["data"]["sessions"][0]["session_key"] == 9877


async def test_f1_get_sessions_invalid_year():
    from sportiq.f1 import tools

    result = await tools.f1_get_sessions(year=2000)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_f1_get_sessions_all_sources_failed():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_sessions_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.f1_get_sessions(year=2025)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_f1_get_sessions_not_found_returns_envelope():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_sessions_chain") as mock:
        mock.fetch = AsyncMock(side_effect=NotFoundError("missing"))
        result = await tools.f1_get_sessions(year=2025)
    assert result["error"]["code"] == "NOT_FOUND"


async def test_f1_weather_intel_not_found_returns_envelope():
    from sportiq.f1 import intel_tools

    with patch("sportiq.f1.intel_tools.f1_weather_chain") as mock:
        mock.fetch = AsyncMock(side_effect=NotFoundError("missing"))
        result = await intel_tools.f1_weather_strategy_impact(session_key=9877)
    assert result["error"]["code"] == "NOT_FOUND"


async def test_f1_get_lap_times_returns_envelope():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_laps_chain") as mock:
        mock.fetch = AsyncMock(
            return_value=_fr({"laps": [{"lap_number": 1, "lap_duration": 83.2}]})
        )
        result = await tools.f1_get_lap_times(session_key=9877, driver_number=1)
    assert "data" in result
    assert result["data"]["laps"][0]["lap_duration"] == 83.2


async def test_f1_get_weather_returns_envelope():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_weather_chain") as mock:
        mock.fetch = AsyncMock(
            return_value=_fr({"weather": [{"rainfall": 0, "track_temperature": 38.0}]})
        )
        result = await tools.f1_get_weather(session_key=9877)
    assert "data" in result


async def test_f1_get_race_results_returns_envelope():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_results_chain") as mock:
        mock.fetch = AsyncMock(
            return_value=_fr({"results": {"MRData": {"RaceTable": {"round": "1"}}}}, source="jolpica")
        )
        result = await tools.f1_get_race_results(year=2025, round=1)
    assert "data" in result
    assert result["data"]["results"]["MRData"]["RaceTable"]["round"] == "1"
    assert result["meta"]["source"] == "jolpica"


async def test_f1_get_race_results_invalid_round():
    from sportiq.f1 import tools

    result = await tools.f1_get_race_results(year=2025, round=0)
    assert result["error"]["code"] == "INVALID_INPUT"


# -- f1_get_drivers -----------------------------------------------------------


async def test_f1_get_drivers_returns_envelope():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_drivers_chain") as mock:
        mock.fetch = AsyncMock(
            return_value=_fr({"drivers": [{"driver_number": 1, "full_name": "Max Verstappen", "team": "Red Bull"}]})
        )
        result = await tools.f1_get_drivers(session_key=9877)
    assert "data" in result and "meta" in result
    assert result["data"]["drivers"][0]["driver_number"] == 1


async def test_f1_get_drivers_invalid_session_key():
    from sportiq.f1 import tools

    result = await tools.f1_get_drivers(session_key=0)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_f1_get_drivers_all_sources_failed():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_drivers_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.f1_get_drivers(session_key=9877)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- f1_get_standings ---------------------------------------------------------


async def test_f1_get_standings_returns_envelope():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_standings_chain") as mock:
        mock.fetch = AsyncMock(
            return_value=_fr({"driver_standings": [{"position": 1, "driver": "Max Verstappen", "points": 87.0}], "constructor_standings": []})
        )
        result = await tools.f1_get_standings(year=2025)
    assert result["data"]["driver_standings"][0]["position"] == 1


async def test_f1_get_standings_invalid_year():
    from sportiq.f1 import tools

    result = await tools.f1_get_standings(year=2000)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_f1_get_standings_all_sources_failed():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_standings_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.f1_get_standings(year=2025)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- f1_get_lap_times ---------------------------------------------------------


async def test_f1_get_lap_times_invalid_session_key():
    from sportiq.f1 import tools

    result = await tools.f1_get_lap_times(session_key=0, driver_number=1)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_f1_get_lap_times_invalid_driver_number():
    from sportiq.f1 import tools

    result = await tools.f1_get_lap_times(session_key=9877, driver_number=0)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_f1_get_lap_times_all_sources_failed():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_laps_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.f1_get_lap_times(session_key=9877, driver_number=1)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- f1_get_weather -----------------------------------------------------------


async def test_f1_get_weather_invalid_session_key():
    from sportiq.f1 import tools

    result = await tools.f1_get_weather(session_key=0)
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_f1_get_weather_all_sources_failed():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_weather_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.f1_get_weather(session_key=9877)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


# -- f1_get_race_results ------------------------------------------------------


async def test_f1_get_race_results_all_sources_failed():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_results_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await tools.f1_get_race_results(year=2025, round=1)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_f1_get_race_results_invalid_year():
    from sportiq.f1 import tools

    result = await tools.f1_get_race_results(year=2000, round=1)
    assert result["error"]["code"] == "INVALID_INPUT"


# -- envelope meta fields -----------------------------------------------------


async def test_f1_meta_has_required_fields():
    from sportiq.f1 import tools

    with patch("sportiq.f1.tools.f1_sessions_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr({"sessions": [{"session_key": 9877}]}))
        result = await tools.f1_get_sessions(year=2025)
    for field in ["source", "is_stale", "data_age_seconds", "fallback_used", "duration_ms"]:
        assert field in result["meta"]
