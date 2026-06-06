"""F1 INTEL tool tests — chains stubbed, envelope shape asserted."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from sportiq.core.errors import AllSourcesFailedError
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


def _laps_payload(n: int = 10, slope: float = 0.08) -> dict:
    return {
        "laps": [
            {"lap_duration": 83.0 + slope * i, "compound": "SOFT", "tyre_life": i}
            for i in range(n)
        ]
    }


# -- f1_tyre_degradation -------------------------------------------------------


async def test_f1_tyre_degradation_returns_model():
    from sportiq.f1 import intel_tools

    with (
        patch("sportiq.f1.intel_tools.f1_laps_chain") as mock_laps,
        patch("sportiq.f1.intel_tools.f1_stints_chain") as mock_stints,
    ):
        mock_laps.fetch = AsyncMock(return_value=_fr(_laps_payload()))
        mock_stints.fetch = AsyncMock(return_value=_fr({"stints": []}))
        result = await intel_tools.f1_tyre_degradation(
            session_key=9877, driver_number=1, compound="SOFT"
        )
    assert "data" in result
    assert result["meta"]["estimated"] is True
    assert result["meta"]["is_stale"] is False
    assert "slope" in result["data"]


async def test_f1_tyre_degradation_invalid_compound():
    from sportiq.f1 import intel_tools

    result = await intel_tools.f1_tyre_degradation(
        session_key=9877, driver_number=1, compound="SUPER"
    )
    assert result["error"]["code"] == "INVALID_INPUT"


async def test_f1_tyre_degradation_all_sources_failed():
    from sportiq.f1 import intel_tools

    with (
        patch("sportiq.f1.intel_tools.f1_laps_chain") as mock_laps,
        patch("sportiq.f1.intel_tools.f1_stints_chain") as mock_stints,
    ):
        mock_laps.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        mock_stints.fetch = AsyncMock(return_value=_fr({"stints": []}))
        result = await intel_tools.f1_tyre_degradation(
            session_key=9877, driver_number=1, compound="SOFT"
        )
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_f1_tyre_degradation_degrades_gracefully_when_stints_down():
    # Stints source down but laps available (carrying compound, e.g. fastf1):
    # the tool fits on the laps rather than failing the whole request.
    from sportiq.f1 import intel_tools

    with (
        patch("sportiq.f1.intel_tools.f1_laps_chain") as mock_laps,
        patch("sportiq.f1.intel_tools.f1_stints_chain") as mock_stints,
    ):
        mock_laps.fetch = AsyncMock(return_value=_fr(_laps_payload()))
        mock_stints.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await intel_tools.f1_tyre_degradation(
            session_key=9877, driver_number=1, compound="SOFT"
        )
    assert "data" in result
    assert result["meta"]["stint_enrichment"] is False
    assert result["data"]["slope"] > 0


# -- f1_undercut_window --------------------------------------------------------


async def test_f1_undercut_window_returns_viability():
    from sportiq.f1 import intel_tools

    with patch("sportiq.f1.intel_tools.f1_laps_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_laps_payload()))
        result = await intel_tools.f1_undercut_window(
            session_key=9877, attacker_number=1, target_number=16, current_lap=25
        )
    assert "data" in result
    assert "viable" in result["data"]
    assert result["meta"]["estimated"] is True


async def test_f1_undercut_window_invalid_args():
    from sportiq.f1 import intel_tools

    result = await intel_tools.f1_undercut_window(
        session_key=0, attacker_number=1, target_number=16, current_lap=25
    )
    assert result["error"]["code"] == "INVALID_INPUT"


# -- f1_head_to_head_pace ------------------------------------------------------


async def test_f1_head_to_head_pace_returns_delta():
    from sportiq.f1 import intel_tools

    with patch("sportiq.f1.intel_tools.f1_laps_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_laps_payload()))
        result = await intel_tools.f1_head_to_head_pace(
            session_key=9877, driver_a=1, driver_b=16
        )
    assert "data" in result
    assert "delta_s" in result["data"]


async def test_f1_head_to_head_pace_all_sources_failed():
    from sportiq.f1 import intel_tools

    with patch("sportiq.f1.intel_tools.f1_laps_chain") as mock:
        mock.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        result = await intel_tools.f1_head_to_head_pace(
            session_key=9877, driver_a=1, driver_b=16
        )
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"


async def test_f1_head_to_head_pace_tie_has_no_faster_driver():
    """Identical pace (delta == 0) is a tie, not a default win for driver_b."""
    from sportiq.f1 import intel_tools

    with patch("sportiq.f1.intel_tools.f1_laps_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(_laps_payload()))
        result = await intel_tools.f1_head_to_head_pace(
            session_key=9877, driver_a=1, driver_b=16
        )
    assert result["data"]["delta_s"] == 0.0
    assert result["data"]["faster_driver"] is None


# -- f1_weather_strategy_impact -----------------------------------------------


async def test_f1_weather_strategy_impact_returns_recommendation():
    from sportiq.f1 import intel_tools

    weather_payload = {"weather": [{"rainfall": 0, "track_temperature": 38.0}]}
    with patch("sportiq.f1.intel_tools.f1_weather_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(weather_payload))
        result = await intel_tools.f1_weather_strategy_impact(session_key=9877)
    assert "data" in result
    assert "recommendation" in result["data"]
    assert result["meta"]["estimated"] is True


async def test_f1_weather_strategy_impact_rain_recommends_inter():
    from sportiq.f1 import intel_tools

    weather_payload = {"weather": [{"rainfall": 2.0, "track_temperature": 18.0}]}
    with patch("sportiq.f1.intel_tools.f1_weather_chain") as mock:
        mock.fetch = AsyncMock(return_value=_fr(weather_payload))
        result = await intel_tools.f1_weather_strategy_impact(session_key=9877)
    assert result["data"]["compound_recommendation"] == "INTER"


# -- f1_predict_pit_strategy (flagship) ----------------------------------------


async def test_f1_predict_pit_strategy_returns_stop_laps():
    from sportiq.f1 import intel_tools

    laps_p = {
        "laps": [
            {"lap_duration": 83.0 + 0.08 * i, "compound": "SOFT", "tyre_life": i}
            for i in range(25)
        ]
    }
    stints_p = {"stints": [{"compound": "SOFT", "lap_start": 1, "lap_end": 25}]}
    weather_p = {"weather": [{"rainfall": 0, "track_temperature": 35.0}]}
    with (
        patch("sportiq.f1.intel_tools.f1_laps_chain") as mock_laps,
        patch("sportiq.f1.intel_tools.f1_stints_chain") as mock_stints,
        patch("sportiq.f1.intel_tools.f1_weather_chain") as mock_weather,
    ):
        mock_laps.fetch = AsyncMock(return_value=_fr(laps_p))
        mock_stints.fetch = AsyncMock(return_value=_fr(stints_p))
        mock_weather.fetch = AsyncMock(return_value=_fr(weather_p))
        result = await intel_tools.f1_predict_pit_strategy(
            session_key=9877, driver_number=1, current_lap=15, total_laps=57
        )
    assert "data" in result
    assert "stop_laps" in result["data"]
    assert result["meta"]["estimated"] is True
    assert isinstance(result["data"]["stop_laps"], list)


async def test_f1_predict_pit_strategy_infers_total_laps_from_lap_numbers():
    from sportiq.f1 import intel_tools

    # 78 laps observed (Monaco length). Caller omits total_laps, so it should be
    # inferred as 78 rather than the old hard-coded 57.
    laps_p = {
        "laps": [
            {"lap_number": i, "lap_duration": 80.0 + 0.05 * i, "compound": "SOFT", "tyre_life": i}
            for i in range(1, 79)
        ]
    }
    with (
        patch("sportiq.f1.intel_tools.f1_laps_chain") as mock_laps,
        patch("sportiq.f1.intel_tools.f1_stints_chain") as mock_stints,
        patch("sportiq.f1.intel_tools.f1_weather_chain") as mock_weather,
    ):
        mock_laps.fetch = AsyncMock(return_value=_fr(laps_p))
        mock_stints.fetch = AsyncMock(return_value=_fr({"stints": []}))
        mock_weather.fetch = AsyncMock(return_value=_fr({"weather": []}))
        result = await intel_tools.f1_predict_pit_strategy(session_key=9877, driver_number=1)
    assert result["meta"]["total_laps"] == 78


async def test_f1_predict_pit_strategy_all_sources_failed():
    from sportiq.f1 import intel_tools

    with (
        patch("sportiq.f1.intel_tools.f1_laps_chain") as mock_laps,
        patch("sportiq.f1.intel_tools.f1_stints_chain") as mock_stints,
        patch("sportiq.f1.intel_tools.f1_weather_chain") as mock_weather,
    ):
        mock_laps.fetch = AsyncMock(side_effect=AllSourcesFailedError("failed", attempts=[]))
        mock_stints.fetch = AsyncMock(return_value=_fr({"stints": []}))
        mock_weather.fetch = AsyncMock(return_value=_fr({"weather": []}))
        result = await intel_tools.f1_predict_pit_strategy(session_key=9877, driver_number=1)
    assert result["error"]["code"] == "ALL_SOURCES_FAILED"
